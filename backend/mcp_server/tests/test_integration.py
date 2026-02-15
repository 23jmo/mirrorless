"""Integration tests — connect MCP client to our server and call tools.

These tests verify the MCP protocol layer: tool discovery, schema correctness,
and end-to-end tool execution (with mocked external dependencies).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Client

from mcp_server.server import mcp


@pytest.fixture
def mock_serper():
    """Mock the Serper API HTTP calls."""
    with patch("mcp_server.shopping.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "shopping": [
                {
                    "title": "Test Jacket",
                    "source": "TestStore",
                    "price": "$99.99",
                    "imageUrl": "https://example.com/jacket.jpg",
                    "link": "https://example.com/jacket",
                    "productId": "test-123",
                }
            ]
        }
        mock_resp.raise_for_status.return_value = None
        mock_client.post.return_value = mock_resp
        yield mock_client


@pytest.fixture
def mock_backend():
    """Mock the backend HTTP calls for mirror bridge tools."""
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
async def test_mcp_server_lists_all_tools():
    """MCP client discovers all 5 tools with correct names."""
    async with Client(mcp) as client:
        tools = await client.list_tools()
        tool_names = {t.name for t in tools}

        assert tool_names == {
            "search_clothing",
            "present_items",
            "send_to_mirror",
            "get_past_sessions",
            "save_session",
        }


@pytest.mark.asyncio
async def test_search_clothing_via_mcp_client(mock_serper):
    """Call search_clothing through MCP client protocol."""
    with patch.dict("os.environ", {"SERPER_API_KEY": "test-key"}):
        async with Client(mcp) as client:
            result = await client.call_tool(
                "search_clothing",
                {"query": "mens black jacket", "num_results": 5},
            )

            assert not result.is_error
            assert len(result.content) > 0
            text_content = str(result.content)
            assert "Test Jacket" in text_content


@pytest.mark.asyncio
async def test_present_items_via_mcp_client(mock_backend):
    """Call present_items through MCP client protocol."""
    mock_backend.post.return_value = _ok_response({
        "ok": True, "presented": 1, "mirror_id": "MIRROR-A1",
    })

    async with Client(mcp) as client:
        result = await client.call_tool(
            "present_items",
            {
                "mirror_id": "MIRROR-A1",
                "items": [
                    {
                        "title": "Test Jacket",
                        "price": "$99.99",
                        "image_url": "https://example.com/jacket.jpg",
                        "link": "https://example.com/jacket",
                        "source": "TestStore",
                    }
                ],
            },
        )

        assert not result.is_error
        assert len(result.content) > 0
        mock_backend.post.assert_called_once()


@pytest.mark.asyncio
async def test_send_to_mirror_via_mcp_client(mock_backend):
    """Call send_to_mirror through MCP client protocol."""
    mock_backend.post.return_value = _ok_response({
        "ok": True, "mirror_id": "MIRROR-A1",
    })

    async with Client(mcp) as client:
        result = await client.call_tool(
            "send_to_mirror",
            {
                "mirror_id": "MIRROR-A1",
                "text": "Looking great! Let me find some options.",
            },
        )

        assert not result.is_error
        assert len(result.content) > 0
        mock_backend.post.assert_called_once()


@pytest.mark.asyncio
async def test_session_roundtrip_via_mcp_client(mock_backend):
    """Save a session then retrieve it through MCP client."""
    mock_backend.post.return_value = _ok_response({
        "ok": True, "session_id": "s-123", "mirror_id": "MIRROR-A1",
    })

    mock_backend.get.return_value = _ok_response({
        "sessions": [
            {
                "session_id": "s-123",
                "started_at": "2026-02-14T10:00:00Z",
                "status": "completed",
                "items": [{"data": {"title": "Navy Blazer"}, "reaction": "liked"}],
            }
        ],
        "mirror_id": "MIRROR-A1",
    })

    async with Client(mcp) as client:
        # Save session
        save_result = await client.call_tool(
            "save_session",
            {
                "mirror_id": "MIRROR-A1",
                "summary": "Looked at date night outfits",
                "items_shown": [{"title": "Navy Blazer", "price": "$89"}],
                "reactions": {"likes": 1, "items_shown": 1},
            },
        )
        assert not save_result.is_error

        # Get past sessions
        get_result = await client.call_tool(
            "get_past_sessions",
            {"mirror_id": "MIRROR-A1", "limit": 5},
        )
        assert not get_result.is_error
        text = str(get_result.content)
        assert "s-123" in text or "sessions" in text
