"""FastAPI routes for the scraping pipeline."""

import asyncio
from collections import OrderedDict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from models.database import get_neon_client
from scraper.gmail_auth import exchange_auth_code
from scraper.pipeline import fast_scrape
from scraper.profile_builder import build_style_profile
from scraper.brand_scanner import scan_brand_frequency
from scraper.db import (
    store_purchases, store_style_profile, get_user_token, store_user_token,
    get_last_scraped_at, set_last_scraped_at, get_all_purchases,
    store_calendar_events,
)
from scraper import calendar_fetch
from scraper.socket_events import emit_purchase_found, emit_scrape_progress, emit_scrape_complete

router = APIRouter(prefix="/api/scrape", tags=["scraping"])

# ── In-memory scrape job tracking (max 50, evict oldest completed) ──

MAX_SCRAPE_JOBS = 50
_scrape_jobs: OrderedDict[str, dict] = OrderedDict()


def _update_scrape_job(user_id: str, **updates):
    """Update an existing scrape job entry."""
    if user_id in _scrape_jobs:
        _scrape_jobs[user_id].update(updates)


def _complete_scrape_job(user_id: str, status: str, error: str | None = None):
    """Mark a scrape job as completed or failed, then evict excess entries."""
    if user_id in _scrape_jobs:
        _scrape_jobs[user_id].update(
            status=status,
            completed_at=datetime.now(timezone.utc).isoformat(),
            error=error,
        )
    # Evict oldest completed jobs when over limit
    while len(_scrape_jobs) > MAX_SCRAPE_JOBS:
        oldest_key = next(iter(_scrape_jobs))
        if _scrape_jobs[oldest_key]["status"] in ("completed", "failed"):
            _scrape_jobs.pop(oldest_key)
        else:
            break


def get_scrape_jobs() -> list[dict]:
    """Return all scrape jobs, newest first."""
    return list(reversed(_scrape_jobs.values()))


class AuthRequest(BaseModel):
    user_id: str
    auth_code: str
    redirect_uri: str


class ScrapeRequest(BaseModel):
    user_id: str


@router.post("/auth")
async def exchange_token(req: AuthRequest):
    """Exchange Google OAuth auth code for tokens and store them."""
    try:
        token_data = exchange_auth_code(req.auth_code, req.redirect_uri)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {e}")

    db = await get_neon_client()
    try:
        await store_user_token(db, req.user_id, token_data)
    finally:
        await db.close()

    return {"status": "ok"}


@router.post("/start")
async def start_scrape(req: ScrapeRequest, request: Request):
    """Kick off streaming scrape in background. Results arrive via Socket.io."""
    db = await get_neon_client()
    try:
        token_data = await get_user_token(db, req.user_id)
        if not token_data:
            raise HTTPException(status_code=400, detail="No OAuth token for user. Complete /auth first.")

        # Look up user name for admin display
        name_row = await db.fetchval(
            "SELECT name FROM users WHERE id = $1::uuid", [req.user_id]
        )
        user_name = name_row or "Unknown"
    finally:
        await db.close()

    # Register scrape job for admin monitoring
    _scrape_jobs[req.user_id] = {
        "user_id": req.user_id,
        "user_name": user_name,
        "status": "running",
        "phase": "starting",
        "purchases_found": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "error": None,
    }
    # Move to end so newest is last (reversed in get_scrape_jobs)
    _scrape_jobs.move_to_end(req.user_id)

    sio = request.app.state.sio
    asyncio.create_task(_background_scrape(req.user_id, token_data, sio))

    return {"status": "started"}


async def _background_scrape(user_id: str, token_data: dict, sio):
    """Run scrape in background, streaming results via Socket.io.

    Incremental: if the user has been scraped before, only fetches emails
    newer than last_scraped_at. Profile is always rebuilt from ALL purchases.
    Also fetches calendar events in parallel (failure doesn't block Gmail).
    """
    db = await get_neon_client()
    try:
        _update_scrape_job(user_id, phase="searching")
        await emit_scrape_progress(sio, user_id, 0, [], "searching")

        # Check for previous scrape timestamp
        last_scraped = await get_last_scraped_at(db, user_id)

        total_count = [0]  # mutable counter for closure

        async def on_email(email, purchases):
            total_count[0] += len(purchases)
            _update_scrape_job(user_id, phase="parsing", purchases_found=total_count[0])
            # Store each batch immediately
            await store_purchases(db, user_id, purchases)
            # Stream to frontend
            await emit_purchase_found(
                sio, user_id,
                email_subject=email.get("subject", ""),
                purchases=purchases,
                total_so_far=total_count[0],
            )

        result = await fast_scrape(token_data, on_email=on_email, since=last_scraped)

        # Mark scrape timestamp before profile rebuild
        await set_last_scraped_at(db, user_id)

        # Rebuild profile from ALL purchases (old + new) for full accuracy
        _update_scrape_job(user_id, phase="profiling")
        all_purchases = await get_all_purchases(db, user_id)
        profile = build_style_profile(all_purchases, result.brand_freq)

        # Store final profile
        await store_style_profile(db, user_id, profile)

        # Fetch calendar events in parallel (non-blocking, failures are ok)
        try:
            loop = asyncio.get_event_loop()
            service = await loop.run_in_executor(
                None, calendar_fetch.build_calendar_service, token_data
            )
            events = await loop.run_in_executor(
                None, calendar_fetch.fetch_events, service
            )
            await store_calendar_events(db, user_id, events)
            print(f"[scrape] Stored {len(events)} calendar events for {user_id}")
        except Exception as cal_err:
            print(f"[scrape] Calendar fetch failed for {user_id} (non-fatal): {cal_err}")

        # Emit completion with profile
        await emit_scrape_complete(sio, user_id, profile)
        _complete_scrape_job(user_id, "completed")

    except Exception as e:
        print(f"[scrape] Error for user {user_id}: {e}")
        await emit_scrape_progress(sio, user_id, 0, [], "error")
        _complete_scrape_job(user_id, "failed", error=str(e))
    finally:
        await db.close()
