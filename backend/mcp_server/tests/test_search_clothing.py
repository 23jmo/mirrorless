"""Tests for the search_clothing MCP tool (Serper API client)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_server.shopping import search_serper, _parse_price


# --- Sample Serper API responses ---

SAMPLE_SERPER_RESPONSE = {
    "shopping": [
        {
            "title": "Nike Air Max 90",
            "source": "Nike.com",
            "price": "$129.99",
            "imageUrl": "https://example.com/nike.jpg",
            "link": "https://nike.com/air-max-90",
            "productId": "abc123",
            "rating": 4.5,
            "ratingCount": 120,
        },
        {
            "title": "Adidas Ultraboost 22",
            "source": "Adidas.com",
            "price": "$189.00",
            "imageUrl": "https://example.com/adidas.jpg",
            "link": "https://adidas.com/ultraboost",
            "productId": "def456",
            "rating": 4.7,
            "ratingCount": 85,
        },
        {
            "title": "New Balance 550",
            "source": "New Balance",
            "price": "$109.99",
            "imageUrl": "https://example.com/nb.jpg",
            "link": "https://newbalance.com/550",
            "productId": "ghi789",
        },
    ]
}

SERPER_URL = "https://google.serper.dev/shopping"


def _make_mock_response(response_json, status_code=200):
    """Create a mock httpx Response (sync methods like json() and raise_for_status())."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = response_json
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=httpx.Request("POST", SERPER_URL),
            response=httpx.Response(status_code),
        )
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


@pytest.fixture
def mock_serper():
    """Patch httpx.AsyncClient to return controlled Serper responses."""
    with patch("mcp_server.shopping.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock_client


@pytest.mark.asyncio
async def test_search_clothing_returns_structured_results(mock_serper):
    """Serper results are normalized into consistent product dicts."""
    mock_serper.post.return_value = _make_mock_response(SAMPLE_SERPER_RESPONSE)

    with patch.dict("os.environ", {"SERPER_API_KEY": "test-key"}):
        result = await search_serper("mens sneakers", num_results=3)

    assert "results" in result
    assert len(result["results"]) == 3

    item = result["results"][0]
    assert item["title"] == "Nike Air Max 90"
    assert item["price"] == "$129.99"
    assert item["price_numeric"] == 129.99
    assert item["image_url"] == "https://example.com/nike.jpg"
    assert item["link"] == "https://nike.com/air-max-90"
    assert item["source"] == "Nike.com"
    assert item["product_id"] == "abc123"


@pytest.mark.asyncio
async def test_search_clothing_handles_empty_results(mock_serper):
    """Empty Serper response returns empty list without error."""
    mock_serper.post.return_value = _make_mock_response({"shopping": []})

    with patch.dict("os.environ", {"SERPER_API_KEY": "test-key"}):
        result = await search_serper("nonexistent brand xyz")

    assert "results" in result
    assert len(result["results"]) == 0
    assert "error" not in result


@pytest.mark.asyncio
async def test_search_clothing_handles_serper_error(mock_serper):
    """Serper HTTP 500 returns error dict, doesn't crash."""
    mock_serper.post.return_value = _make_mock_response({}, status_code=500)

    with patch.dict("os.environ", {"SERPER_API_KEY": "test-key"}):
        result = await search_serper("test query")

    assert "error" in result
    assert "500" in result["error"]
    assert result["results"] == []


@pytest.mark.asyncio
async def test_search_clothing_default_num_results(mock_serper):
    """Default num_results is 8 when not specified."""
    mock_serper.post.return_value = _make_mock_response(SAMPLE_SERPER_RESPONSE)

    with patch.dict("os.environ", {"SERPER_API_KEY": "test-key"}):
        await search_serper("test query")

    call_args = mock_serper.post.call_args
    assert call_args[1]["json"]["num"] == 8


@pytest.mark.asyncio
async def test_search_clothing_missing_api_key():
    """Missing SERPER_API_KEY returns error without making HTTP call."""
    with patch.dict("os.environ", {}, clear=True):
        import os
        os.environ.pop("SERPER_API_KEY", None)

        result = await search_serper("test query")

    assert "error" in result
    assert "SERPER_API_KEY" in result["error"]
    assert result["results"] == []


# --- Price parser unit tests ---

def test_parse_price_standard():
    assert _parse_price("$129.99") == 129.99


def test_parse_price_with_commas():
    assert _parse_price("$1,299.00") == 1299.0


def test_parse_price_no_decimal():
    assert _parse_price("$50") == 50.0


def test_parse_price_invalid():
    assert _parse_price("Free") is None
