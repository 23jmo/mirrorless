"""Tests for the get_past_sessions and save_session MCP tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server.mirror import do_get_past_sessions as get_past_sessions, do_save_session as save_session


@pytest.fixture
def mock_backend():
    """Patch httpx.AsyncClient to mock backend HTTP calls."""
    with patch("mcp_server.mirror.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock_client


def _ok_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


# --- save_session tests ---

@pytest.mark.asyncio
async def test_save_session_calls_backend_endpoint(mock_backend):
    """save_session sends correct payload to backend /api/mirror/sessions."""
    mock_backend.post.return_value = _ok_response({
        "ok": True,
        "session_id": "test-session-id",
        "mirror_id": "MIRROR-A1",
    })

    result = await save_session(
        mirror_id="MIRROR-A1",
        summary="Looked at date night outfits, loved the navy blazer",
        items_shown=[
            {"title": "Navy Blazer", "price": "$89", "reaction": "liked"},
            {"title": "Red Dress", "price": "$120", "reaction": "disliked"},
        ],
        reactions={"likes": 1, "dislikes": 1, "items_shown": 2},
    )

    assert result["ok"] is True
    assert result["session_id"] == "test-session-id"

    call_args = mock_backend.post.call_args
    payload = call_args[1]["json"]
    assert payload["mirror_id"] == "MIRROR-A1"
    assert "summary" in payload
    assert len(payload["items_shown"]) == 2


# --- get_past_sessions tests ---

@pytest.mark.asyncio
async def test_get_past_sessions_returns_history(mock_backend):
    """get_past_sessions returns list of sessions with expected fields."""
    mock_backend.get.return_value = _ok_response({
        "sessions": [
            {
                "session_id": "s1",
                "started_at": "2026-02-14T10:00:00Z",
                "ended_at": "2026-02-14T10:15:00Z",
                "status": "completed",
                "items": [
                    {"data": {"title": "Navy Blazer"}, "reaction": "liked"},
                ],
            }
        ],
        "mirror_id": "MIRROR-A1",
    })

    result = await get_past_sessions("MIRROR-A1")

    assert "sessions" in result
    assert len(result["sessions"]) == 1
    assert result["sessions"][0]["session_id"] == "s1"


@pytest.mark.asyncio
async def test_get_past_sessions_empty_history(mock_backend):
    """Empty history returns empty list, no error."""
    mock_backend.get.return_value = _ok_response({
        "sessions": [],
        "mirror_id": "MIRROR-A1",
    })

    result = await get_past_sessions("MIRROR-A1")

    assert "sessions" in result
    assert len(result["sessions"]) == 0
    assert "error" not in result


@pytest.mark.asyncio
async def test_get_past_sessions_respects_limit(mock_backend):
    """limit param is passed to backend."""
    mock_backend.get.return_value = _ok_response({"sessions": [], "mirror_id": "MIRROR-A1"})

    await get_past_sessions("MIRROR-A1", limit=3)

    call_args = mock_backend.get.call_args
    assert call_args[1]["params"]["limit"] == 3


@pytest.mark.asyncio
async def test_get_past_sessions_backend_unreachable(mock_backend):
    """Connection error returns graceful error response."""
    mock_backend.get.side_effect = httpx.ConnectError("Connection refused")

    result = await get_past_sessions("MIRROR-A1")

    assert "error" in result
    assert "Failed to get sessions" in result["error"]
