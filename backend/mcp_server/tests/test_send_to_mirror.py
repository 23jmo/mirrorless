"""Tests for the send_to_mirror MCP tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server.mirror import do_send_to_mirror as send_to_mirror


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


@pytest.mark.asyncio
async def test_send_to_mirror_calls_backend_endpoint(mock_backend):
    """send_to_mirror sends correct payload to backend /api/mirror/text."""
    mock_backend.post.return_value = _ok_response({"ok": True, "mirror_id": "MIRROR-A1"})

    result = await send_to_mirror("MIRROR-A1", "The navy blazer pairs perfectly!")

    assert result["ok"] is True

    call_args = mock_backend.post.call_args
    payload = call_args[1]["json"]
    assert payload["mirror_id"] == "MIRROR-A1"
    assert payload["text"] == "The navy blazer pairs perfectly!"


@pytest.mark.asyncio
async def test_send_to_mirror_empty_text():
    """Empty text returns error without calling backend."""
    result = await send_to_mirror("MIRROR-A1", "")
    assert "error" in result

    result2 = await send_to_mirror("MIRROR-A1", "   ")
    assert "error" in result2


@pytest.mark.asyncio
async def test_send_to_mirror_backend_unreachable(mock_backend):
    """Connection error returns graceful error response."""
    mock_backend.post.side_effect = httpx.ConnectError("Connection refused")

    result = await send_to_mirror("MIRROR-A1", "Hello mirror!")

    assert "error" in result
    assert "Failed to send to mirror" in result["error"]
