"""FastAPI routes for the scraping pipeline."""

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.database import get_neon_client
from scraper.gmail_auth import exchange_auth_code
from scraper.pipeline import fast_scrape, deep_scrape
from scraper.db import store_purchases, store_style_profile, get_user_token, store_user_token

router = APIRouter(prefix="/api/scrape", tags=["scraping"])


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
async def start_scrape(req: ScrapeRequest):
    """Run fast scrape and return immediate results. Kicks off deep scrape in background."""
    db = await get_neon_client()
    try:
        token_data = await get_user_token(db, req.user_id)
        if not token_data:
            raise HTTPException(status_code=400, detail="No OAuth token for user. Complete /auth first.")

        # Fast scrape (~15s)
        result = await fast_scrape(token_data)

        # Store results
        await store_purchases(db, req.user_id, result.purchases)
        await store_style_profile(db, req.user_id, result.profile)

        # Kick off deep scrape in background (fire-and-forget)
        asyncio.create_task(_background_deep_scrape(req.user_id, token_data))

        return {
            "purchases": result.purchases,
            "brand_freq": result.brand_freq,
            "profile": result.profile,
        }
    finally:
        await db.close()


async def _background_deep_scrape(user_id: str, token_data: dict):
    """Run deep scrape in background and store results incrementally."""
    db = await get_neon_client()
    try:
        async def on_update(partial_result):
            await store_purchases(db, user_id, partial_result.purchases[-5:])
            await store_style_profile(db, user_id, partial_result.profile)

        await deep_scrape(token_data, on_update=on_update)
    except Exception as e:
        print(f"[deep_scrape] Error for user {user_id}: {e}")
    finally:
        await db.close()
