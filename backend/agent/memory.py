"""Session memory for Mira — persistent across sessions."""

import asyncio
import json

from models.database import NeonHTTPClient
from scraper.calendar_fetch import build_calendar_service, fetch_events
from scraper.db import store_calendar_events, get_calendar_events


async def save_session_summary(
    db: NeonHTTPClient,
    session_id: str,
    summary: str,
    liked_items: list[dict],
    reactions: dict,
) -> None:
    """Save a session summary for future Mira context."""
    await db.execute(
        "UPDATE sessions SET ended_at = now(), status = 'completed' WHERE id = $1",
        [session_id],
    )
    # Store summary as outfit_data on a special "summary" record
    await db.execute(
        "INSERT INTO session_outfits (session_id, outfit_data, reaction) "
        "VALUES ($1, $2::jsonb, 'summary')",
        [
            session_id,
            json.dumps({
                "summary": summary,
                "liked_items": liked_items,
                "reactions": reactions,
            }),
        ],
    )


async def load_past_sessions(db: NeonHTTPClient, user_id: str) -> list[dict]:
    """Load past session summaries for a user."""
    rows = await db.execute(
        "SELECT so.outfit_data FROM session_outfits so "
        "JOIN sessions s ON so.session_id = s.id "
        "WHERE s.user_id = $1 AND so.reaction = 'summary' "
        "ORDER BY s.ended_at DESC LIMIT 3",
        [user_id],
    )
    results = []
    for row in rows:
        data = row.get("outfit_data", {})
        if isinstance(data, str):
            data = json.loads(data)
        results.append(data)
    return results


async def load_user_profile(db: NeonHTTPClient, user_id: str) -> dict:
    """Load user profile and style data in a single query."""
    rows = await db.execute(
        "SELECT u.id, u.name, u.email, "
        "sp.brands, sp.price_range, sp.style_tags, sp.size_info, sp.narrative_summary "
        "FROM users u "
        "LEFT JOIN style_profiles sp ON sp.user_id = u.id "
        "WHERE u.id = $1",
        [user_id],
    )
    if not rows:
        return {}

    user = rows[0]
    style = user  # All columns are in the same row now

    # Parse array fields from postgres format
    brands = style.get("brands", [])
    if isinstance(brands, str):
        brands = [b.strip() for b in brands.strip("{}").split(",") if b.strip()]

    style_tags = style.get("style_tags", [])
    if isinstance(style_tags, str):
        style_tags = [t.strip() for t in style_tags.strip("{}").split(",") if t.strip()]

    price_range = style.get("price_range")
    if isinstance(price_range, str):
        price_range = json.loads(price_range)

    return {
        "user_id": str(user["id"]),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "brands": brands,
        "price_range": price_range or {},
        "style_tags": style_tags,
        "narrative_summary": style.get("narrative_summary", ""),
    }


async def load_user_purchases(db: NeonHTTPClient, user_id: str) -> list[dict]:
    """Load user's purchase history (all items, with is_fashion flag)."""
    rows = await db.execute(
        "SELECT brand, item_name, category, price, date, is_fashion "
        "FROM purchases WHERE user_id = $1 "
        "ORDER BY date DESC LIMIT 200",
        [user_id],
    )
    return [
        {
            "brand": r.get("brand", ""),
            "item_name": r.get("item_name", ""),
            "category": r.get("category"),
            "price": float(r["price"]) if r.get("price") else None,
            "date": str(r["date"]) if r.get("date") else None,
            "is_fashion": r.get("is_fashion", True),
        }
        for r in rows
    ]


async def get_user_oauth_token(db: NeonHTTPClient, user_id: str) -> dict | None:
    """Get user's OAuth token for Gmail access."""
    rows = await db.execute(
        "SELECT google_oauth_token FROM users WHERE id = $1",
        [user_id],
    )
    if rows and rows[0].get("google_oauth_token"):
        token = rows[0]["google_oauth_token"]
        return token if isinstance(token, dict) else json.loads(token)
    return None


async def load_purchase_statistics(db: NeonHTTPClient, user_id: str) -> dict:
    """Compute aggregate statistics over fashion purchases.

    Uses the is_fashion column for filtering instead of a brand blocklist.
    Returns a dict with: total_count, total_spend, avg_price, min_price, max_price,
    top_brands (list of {brand, count, spend}), categories (list of {category, count, spend}),
    monthly_trend (list of {month, count, spend} for last 6 months).
    """
    base_params = [user_id]

    # 1) Overall aggregates (fashion only)
    agg_rows = await db.execute(
        "SELECT COUNT(*) as total_count, "
        "COALESCE(SUM(price), 0) as total_spend, "
        "COALESCE(AVG(price), 0) as avg_price, "
        "COALESCE(MIN(price), 0) as min_price, "
        "COALESCE(MAX(price), 0) as max_price "
        "FROM purchases WHERE user_id = $1 AND is_fashion = true AND price IS NOT NULL",
        base_params,
    )
    agg = agg_rows[0] if agg_rows else {}

    # 2) Top 10 brands by frequency (fashion only)
    brand_rows = await db.execute(
        "SELECT brand, COUNT(*) as count, COALESCE(SUM(price), 0) as spend "
        "FROM purchases WHERE user_id = $1 AND is_fashion = true "
        "GROUP BY brand ORDER BY count DESC LIMIT 10",
        base_params,
    )

    # 3) Category breakdown (fashion only)
    cat_rows = await db.execute(
        "SELECT category, COUNT(*) as count, COALESCE(SUM(price), 0) as spend "
        "FROM purchases WHERE user_id = $1 AND is_fashion = true AND category IS NOT NULL "
        "GROUP BY category ORDER BY count DESC",
        base_params,
    )

    # 4) Monthly spending trend (fashion only, last 6 months)
    trend_rows = await db.execute(
        "SELECT TO_CHAR(date, 'YYYY-MM') as month, COUNT(*) as count, "
        "COALESCE(SUM(price), 0) as spend "
        "FROM purchases WHERE user_id = $1 AND is_fashion = true "
        "AND date >= CURRENT_DATE - INTERVAL '6 months' "
        "GROUP BY TO_CHAR(date, 'YYYY-MM') ORDER BY month DESC",
        base_params,
    )

    return {
        "total_count": int(agg.get("total_count", 0)),
        "total_spend": round(float(agg.get("total_spend", 0)), 2),
        "avg_price": round(float(agg.get("avg_price", 0)), 2),
        "min_price": round(float(agg.get("min_price", 0)), 2),
        "max_price": round(float(agg.get("max_price", 0)), 2),
        "top_brands": [
            {"brand": r["brand"], "count": int(r["count"]), "spend": round(float(r["spend"]), 2)}
            for r in brand_rows
        ],
        "categories": [
            {"category": r["category"], "count": int(r["count"]), "spend": round(float(r["spend"]), 2)}
            for r in cat_rows
        ],
        "monthly_trend": [
            {"month": r["month"], "count": int(r["count"]), "spend": round(float(r["spend"]), 2)}
            for r in trend_rows
        ],
    }


async def load_calendar_events(db: NeonHTTPClient, user_id: str) -> list[dict]:
    """Load cached calendar events from DB (past 7 days through next 14 days).

    Same pattern as load_user_purchases() — reads from DB, no Google API call.
    """
    rows = await get_calendar_events(db, user_id, days_back=7, days_forward=14)
    return [
        {
            "google_event_id": r.get("google_event_id", ""),
            "title": r.get("title", ""),
            "start_time": str(r["start_time"]) if r.get("start_time") else None,
            "end_time": str(r["end_time"]) if r.get("end_time") else None,
            "location": r.get("location"),
            "description": r.get("description"),
            "attendee_count": int(r.get("attendee_count", 0)),
            "is_all_day": r.get("is_all_day", False),
            "status": r.get("status"),
        }
        for r in rows
    ]


async def refresh_calendar_events(
    db: NeonHTTPClient, user_id: str, token_data: dict
) -> list[dict]:
    """Live-fetch calendar events from Google Calendar API, store in DB, return them.

    Uses run_in_executor because googleapiclient is synchronous (httplib2).
    Called at session start for freshness.
    """
    loop = asyncio.get_event_loop()

    # Build service and fetch events in a thread (blocking I/O)
    service = await loop.run_in_executor(None, build_calendar_service, token_data)
    events = await loop.run_in_executor(None, fetch_events, service)

    # Store in DB (async)
    if events:
        await store_calendar_events(db, user_id, events)

    # Return from DB to get consistent formatting
    return await load_calendar_events(db, user_id)
