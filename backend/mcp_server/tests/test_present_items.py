"""Tests for the present_items MCP tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server.mirror import do_present_items as present_items


SAMPLE_ITEMS = [
    {
        "title": "Nike Air Max 90",
        "price": "$129.99",
        "image_url": "https://example.com/nike.jpg",
        "link": "https://nike.com/air-max-90",
        "source": "Nike.com",
    },
    {
        "title": "Adidas Ultraboost",
        "price": "$189.00",
        "image_url": "https://example.com/adidas.jpg",
        "link": "https://adidas.com/ultraboost",
        "source": "Adidas.com",
    },
]


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
async def test_present_items_calls_backend_endpoint(mock_backend):
    """present_items sends correct payload to backend /api/mirror/present."""
    mock_backend.post.return_value = _ok_response({"ok": True, "presented": 2, "mirror_id": "MIRROR-A1"})

    result = await present_items("MIRROR-A1", SAMPLE_ITEMS)

    assert result["ok"] is True
    assert result["presented"] == 2

    call_args = mock_backend.post.call_args
    payload = call_args[1]["json"]
    assert payload["mirror_id"] == "MIRROR-A1"
    assert len(payload["items"]) == 2


@pytest.mark.asyncio
async def test_present_items_validates_item_fields(mock_backend):
    """Items missing required fields return an error."""
    incomplete_items = [{"title": "Missing fields"}]

    result = await present_items("MIRROR-A1", incomplete_items)

    assert "error" in result
    assert "missing required fields" in result["error"].lower()


@pytest.mark.asyncio
async def test_present_items_max_5_items(mock_backend):
    """Only the first 5 items are sent when more are provided."""
    mock_backend.post.return_value = _ok_response({"ok": True, "presented": 5, "mirror_id": "MIRROR-A1"})

    many_items = [
        {
            "title": f"Item {i}",
            "price": f"${i * 10}",
            "image_url": f"https://example.com/{i}.jpg",
            "link": f"https://example.com/{i}",
            "source": "TestStore",
        }
        for i in range(7)
    ]

    await present_items("MIRROR-A1", many_items)

    call_args = mock_backend.post.call_args
    assert len(call_args[1]["json"]["items"]) == 5


@pytest.mark.asyncio
async def test_present_items_empty_list():
    """Empty items list returns error without calling backend."""
    result = await present_items("MIRROR-A1", [])

    assert "error" in result
    assert result["presented"] == 0


@pytest.mark.asyncio
async def test_present_items_backend_unreachable(mock_backend):
    """Connection error returns graceful error response."""
    mock_backend.post.side_effect = httpx.ConnectError("Connection refused")

    result = await present_items("MIRROR-A1", SAMPLE_ITEMS)

    assert "error" in result
    assert "Failed to present items" in result["error"]
