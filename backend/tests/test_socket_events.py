"""Tests for Socket.io scrape progress events."""

import pytest
from unittest.mock import AsyncMock
from scraper.socket_events import emit_scrape_progress, emit_scrape_complete


@pytest.mark.asyncio
async def test_emit_scrape_progress():
    """emit_scrape_progress emits scrape_progress event to user's room."""
    sio = AsyncMock()
    await emit_scrape_progress(
        sio,
        user_id="user-123",
        purchases_count=5,
        brands_found=["Nike", "Zara"],
        phase="fast",
    )
    sio.emit.assert_called_once_with(
        "scrape_progress",
        {
            "user_id": "user-123",
            "purchases_count": 5,
            "brands_found": ["Nike", "Zara"],
            "phase": "fast",
        },
        room="user-123",
    )


@pytest.mark.asyncio
async def test_emit_scrape_complete():
    """emit_scrape_complete emits scrape_complete with profile."""
    sio = AsyncMock()
    profile = {"brands": ["Nike"], "price_range": {"min": 50, "max": 200, "avg": 100}}
    await emit_scrape_complete(sio, user_id="user-123", profile=profile)
    sio.emit.assert_called_once()
    call_args = sio.emit.call_args
    assert call_args[0][0] == "scrape_complete"
    assert call_args[0][1]["profile"] == profile
