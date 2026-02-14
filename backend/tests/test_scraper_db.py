"""Tests for scraper database operations (unit tests with mocked DB)."""

import pytest
from unittest.mock import AsyncMock
from scraper.db import store_purchases, store_style_profile, get_user_token


@pytest.mark.asyncio
async def test_store_purchases_inserts_rows():
    """store_purchases inserts each purchase into the purchases table."""
    db = AsyncMock()
    db.execute.return_value = []

    purchases = [
        {
            "brand": "Nike",
            "item_name": "Air Max 90",
            "category": "shoes",
            "price": 129.99,
            "date": "2026-01-15",
            "source_email_id": "msg1",
        },
        {
            "brand": "Zara",
            "item_name": "Slim Jeans",
            "category": "bottoms",
            "price": 49.90,
            "date": "2026-02-01",
            "source_email_id": "msg2",
        },
    ]
    await store_purchases(db, "user-uuid-123", purchases)
    assert db.execute.call_count == 2


@pytest.mark.asyncio
async def test_store_style_profile_upserts():
    """store_style_profile upserts into style_profiles table."""
    db = AsyncMock()
    db.execute.return_value = []

    profile = {
        "brands": ["Nike", "Zara"],
        "price_range": {"min": 49.90, "max": 129.99, "avg": 89.95},
        "style_tags": ["casual", "sneakerhead"],
        "narrative_summary": "Shops at Nike and Zara.",
    }
    await store_style_profile(db, "user-uuid-123", profile)
    db.execute.assert_called_once()
    call_args = db.execute.call_args
    assert "INSERT INTO style_profiles" in call_args[0][0]
    assert "ON CONFLICT" in call_args[0][0]


@pytest.mark.asyncio
async def test_get_user_token_returns_token_data():
    """get_user_token fetches google_oauth_token from users table."""
    db = AsyncMock()
    db.execute.return_value = [{"google_oauth_token": {"access_token": "abc"}}]

    result = await get_user_token(db, "user-uuid-123")
    assert result["access_token"] == "abc"
