"""Database operations for the scraping pipeline."""

import json


async def store_purchases(db, user_id: str, purchases: list[dict]) -> None:
    """Insert parsed purchases into the purchases table."""
    for p in purchases:
        await db.execute(
            "INSERT INTO purchases (user_id, brand, item_name, category, price, date, source_email_id) "
            "VALUES ($1, $2, $3, $4, $5, $6::date, $7)",
            [
                user_id,
                p["brand"],
                p["item_name"],
                p.get("category"),
                p.get("price"),
                p.get("date"),
                p.get("source_email_id"),
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
