"""Session memory for Mira — persistent across sessions."""

import json

from agent.prompts import _NON_FASHION_BRANDS
from models.database import NeonHTTPClient


def _fashion_filter_clause(param_offset: int = 1) -> tuple[str, list[str]]:
    """Generate a SQL WHERE clause to exclude non-fashion brands.

    Returns (clause_str, params_list) where clause_str uses $N placeholders
    starting from param_offset.
    """
    brands = sorted(_NON_FASHION_BRANDS)
    placeholders = ", ".join(f"${i}" for i in range(param_offset, param_offset + len(brands)))
    clause = f"LOWER(brand) NOT IN ({placeholders})"
    return clause, brands


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
    """Load user's purchase history."""
    rows = await db.execute(
        "SELECT brand, item_name, category, price, date "
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
    """Compute aggregate statistics over the full purchase history.

    Returns a dict with: total_count, total_spend, avg_price, min_price, max_price,
    top_brands (list of {brand, count, spend}), categories (list of {category, count, spend}),
    monthly_trend (list of {month, count, spend} for last 6 months).
    """
    filter_clause, filter_params = _fashion_filter_clause(param_offset=2)

    # All three queries share user_id as $1 and filter_params as $2...$N
    base_params = [user_id] + filter_params

    # 1) Overall aggregates
    agg_rows = await db.execute(
        "SELECT COUNT(*) as total_count, "
        "COALESCE(SUM(price), 0) as total_spend, "
        "COALESCE(AVG(price), 0) as avg_price, "
        "COALESCE(MIN(price), 0) as min_price, "
        "COALESCE(MAX(price), 0) as max_price "
        f"FROM purchases WHERE user_id = $1 AND {filter_clause} AND price IS NOT NULL",
        base_params,
    )
    agg = agg_rows[0] if agg_rows else {}

    # 2) Top 10 brands by frequency
    brand_rows = await db.execute(
        "SELECT brand, COUNT(*) as count, COALESCE(SUM(price), 0) as spend "
        f"FROM purchases WHERE user_id = $1 AND {filter_clause} "
        "GROUP BY brand ORDER BY count DESC LIMIT 10",
        base_params,
    )

    # 3) Category breakdown
    cat_rows = await db.execute(
        "SELECT category, COUNT(*) as count, COALESCE(SUM(price), 0) as spend "
        f"FROM purchases WHERE user_id = $1 AND {filter_clause} AND category IS NOT NULL "
        "GROUP BY category ORDER BY count DESC",
        base_params,
    )

    # 4) Monthly spending trend (last 6 months)
    trend_rows = await db.execute(
        "SELECT TO_CHAR(date, 'YYYY-MM') as month, COUNT(*) as count, "
        "COALESCE(SUM(price), 0) as spend "
        f"FROM purchases WHERE user_id = $1 AND {filter_clause} "
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
