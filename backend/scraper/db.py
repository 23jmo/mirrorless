"""Database operations for the scraping pipeline."""

import json
from datetime import datetime, timedelta, timezone


async def store_purchases(db, user_id: str, purchases: list[dict]) -> None:
    """Insert parsed purchases into the purchases table.

    Uses ON CONFLICT to skip duplicates (same user + email + item).
    """
    for p in purchases:
        receipt_text = p.get("receipt_text")
        if receipt_text and len(receipt_text) > 500:
            receipt_text = receipt_text[:500]
        await db.execute(
            "INSERT INTO purchases "
            "(user_id, brand, item_name, category, price, date, source_email_id, "
            "merchant, order_status, tracking_number, receipt_text, is_fashion) "
            "VALUES ($1, $2, $3, $4, $5, $6::date, $7, $8, $9, $10, $11, $12) "
            "ON CONFLICT (user_id, COALESCE(source_email_id, ''), item_name) "
            "DO UPDATE SET is_fashion = EXCLUDED.is_fashion",
            [
                user_id,
                p["brand"],
                p["item_name"],
                p.get("category"),
                p.get("price"),
                p.get("date"),
                p.get("source_email_id"),
                p.get("merchant"),
                p.get("order_status"),
                p.get("tracking_number"),
                receipt_text,
                p.get("is_fashion", True),
            ],
        )


async def store_style_profile(db, user_id: str, profile: dict) -> None:
    """Upsert a style profile for the user."""
    await db.execute(
        "INSERT INTO style_profiles (user_id, brands, price_range, style_tags, narrative_summary) "
        "VALUES ($1, $2, $3::jsonb, $4, $5) "
        "ON CONFLICT (user_id) DO UPDATE SET "
        "brands = EXCLUDED.brands, "
        "price_range = EXCLUDED.price_range, "
        "style_tags = EXCLUDED.style_tags, "
        "narrative_summary = EXCLUDED.narrative_summary",
        [
            user_id,
            "{" + ",".join(profile["brands"]) + "}" if profile["brands"] else "{}",
            json.dumps(profile["price_range"]),
            "{" + ",".join(profile["style_tags"]) + "}" if profile["style_tags"] else "{}",
            profile.get("narrative_summary"),
        ],
    )


async def get_user_token(db, user_id: str) -> dict | None:
    """Fetch the Google OAuth token for a user."""
    rows = await db.execute(
        "SELECT google_oauth_token FROM users WHERE id = $1",
        [user_id],
    )
    if rows and rows[0].get("google_oauth_token"):
        token = rows[0]["google_oauth_token"]
        return token if isinstance(token, dict) else json.loads(token)
    return None


async def store_user_token(db, user_id: str, token_data: dict) -> None:
    """Store Google OAuth token for a user."""
    await db.execute(
        "UPDATE users SET google_oauth_token = $1::jsonb WHERE id = $2",
        [json.dumps(token_data), user_id],
    )


async def get_last_scraped_at(db, user_id: str) -> datetime | None:
    """Fetch the last scrape timestamp for a user."""
    rows = await db.execute(
        "SELECT last_scraped_at FROM users WHERE id = $1",
        [user_id],
    )
    if rows and rows[0].get("last_scraped_at"):
        val = rows[0]["last_scraped_at"]
        if isinstance(val, datetime):
            return val
        return datetime.fromisoformat(val)
    return None


async def set_last_scraped_at(db, user_id: str) -> None:
    """Set the last scrape timestamp to now."""
    await db.execute(
        "UPDATE users SET last_scraped_at = now() WHERE id = $1",
        [user_id],
    )


async def get_all_purchases(db, user_id: str) -> list[dict]:
    """Fetch all purchases for a user (for profile rebuilding after incremental scrape)."""
    rows = await db.execute(
        "SELECT brand, item_name, category, price, date, merchant, order_status, is_fashion "
        "FROM purchases WHERE user_id = $1",
        [user_id],
    )
    return rows or []


async def store_calendar_events(db, user_id: str, events: list[dict]) -> None:
    """Upsert calendar events into the calendar_events table.

    Uses ON CONFLICT DO UPDATE because calendar events are mutable —
    titles, times, locations, and attendees can change after creation.
    """
    for e in events:
        description = e.get("description")
        if description and len(description) > 500:
            description = description[:500]
        await db.execute(
            "INSERT INTO calendar_events "
            "(user_id, google_event_id, title, start_time, end_time, location, "
            "description, attendee_count, is_all_day, status, scraped_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now()) "
            "ON CONFLICT (user_id, google_event_id) DO UPDATE SET "
            "title = EXCLUDED.title, "
            "start_time = EXCLUDED.start_time, "
            "end_time = EXCLUDED.end_time, "
            "location = EXCLUDED.location, "
            "description = EXCLUDED.description, "
            "attendee_count = EXCLUDED.attendee_count, "
            "is_all_day = EXCLUDED.is_all_day, "
            "status = EXCLUDED.status, "
            "scraped_at = now()",
            [
                user_id,
                e["google_event_id"],
                e["title"],
                e["start_time"].isoformat() if isinstance(e["start_time"], datetime) else e["start_time"],
                e["end_time"].isoformat() if isinstance(e.get("end_time"), datetime) else e.get("end_time"),
                e.get("location"),
                description,
                e.get("attendee_count", 0),
                e.get("is_all_day", False),
                e.get("status"),
            ],
        )


async def get_calendar_events(
    db, user_id: str, days_back: int = 7, days_forward: int = 14
) -> list[dict]:
    """Fetch calendar events within a time window, excluding cancelled.

    Returns events ordered by start_time ascending.
    """
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=days_back)).isoformat()
    time_max = (now + timedelta(days=days_forward)).isoformat()

    rows = await db.execute(
        "SELECT google_event_id, title, start_time, end_time, location, "
        "description, attendee_count, is_all_day, status "
        "FROM calendar_events "
        "WHERE user_id = $1 AND start_time >= $2 AND start_time <= $3 "
        "AND (status IS NULL OR status != 'cancelled') "
        "ORDER BY start_time ASC",
        [user_id, time_min, time_max],
    )
    return rows or []
