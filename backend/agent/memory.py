"""Session memory for Mira — persistent across sessions."""

import json

from models.database import NeonHTTPClient


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
    """Load user profile and style data."""
    # Fetch user basic info
    user_rows = await db.execute(
        "SELECT id, name, email FROM users WHERE id = $1",
        [user_id],
    )
    if not user_rows:
        return {}

    user = user_rows[0]

    # Fetch style profile
    style_rows = await db.execute(
        "SELECT brands, price_range, style_tags, size_info, narrative_summary "
        "FROM style_profiles WHERE user_id = $1",
        [user_id],
    )
    style = style_rows[0] if style_rows else {}

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
    """Load user's purchase history."""
    rows = await db.execute(
        "SELECT brand, item_name, category, price, date "
        "FROM purchases WHERE user_id = $1 "
        "ORDER BY date DESC LIMIT 30",
        [user_id],
    )
    return [
        {
            "brand": r.get("brand", ""),
            "item_name": r.get("item_name", ""),
            "category": r.get("category"),
            "price": float(r["price"]) if r.get("price") else None,
            "date": str(r["date"]) if r.get("date") else None,
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
