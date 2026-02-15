"""Tests for agent tool execution functions: _present_items and _display_product."""

import sys
import types

import pytest
from unittest.mock import AsyncMock, patch


# ── present_items ──


@pytest.mark.asyncio
async def test_present_items_returns_clothing_results_payload():
    from agent.tools import _present_items

    items = [
        {"title": "Blue Shirt", "price": "$49", "image_url": "https://img/1.jpg", "link": "https://a.com", "source": "Nike"},
        {"title": "Black Pants", "price": "$79", "image_url": "https://img/2.jpg", "link": "https://b.com", "source": "Zara"},
    ]
    result = await _present_items({"items": items})

    assert result["presented"] == 2
    assert result["frontend_payload"]["type"] == "clothing_results"
    assert len(result["frontend_payload"]["items"]) == 2


@pytest.mark.asyncio
async def test_present_items_caps_at_five():
    from agent.tools import _present_items

    items = [{"title": f"Item {i}", "price": "$10", "image_url": f"https://img/{i}.jpg", "link": "#", "source": "X"} for i in range(10)]
    result = await _present_items({"items": items})

    assert result["presented"] == 5
    assert len(result["frontend_payload"]["items"]) == 5


@pytest.mark.asyncio
async def test_present_items_empty_returns_error():
    from agent.tools import _present_items

    result = await _present_items({"items": []})

    assert "error" in result
    assert result["presented"] == 0


@pytest.mark.asyncio
async def test_present_items_missing_items_key():
    from agent.tools import _present_items

    result = await _present_items({})

    assert "error" in result
    assert result["presented"] == 0


# ── display_product ──


@pytest.mark.asyncio
async def test_display_product_returns_payload():
    from agent.tools import _display_product

    items = [
        {"title": "T-Shirt", "image_url": "https://img/t.jpg", "product_id": "p1"},
        {"title": "Jeans", "image_url": "https://img/j.jpg", "product_id": "p2"},
    ]

    # Create a fake gemini_flatlay module with a mock async function
    fake_module = types.ModuleType("services.gemini_flatlay")
    mock_gen = AsyncMock(return_value={"p1": "data:image/png;base64,flat1"})
    fake_module.generate_flat_lays_batch = mock_gen

    with patch.dict(sys.modules, {"services.gemini_flatlay": fake_module}):
        result = await _display_product({"items": items, "outfit_name": "Casual"})

    assert result["displayed"] == 2
    assert result["frontend_payload"]["type"] == "display_product"
    assert result["frontend_payload"]["outfit_name"] == "Casual"
    # p1 got a flat lay, p2 did not
    assert result["items"][0].get("cleaned_image_url") == "data:image/png;base64,flat1"
    assert result["items"][1].get("cleaned_image_url") is None


@pytest.mark.asyncio
async def test_display_product_gemini_import_error_non_fatal():
    """When gemini_flatlay module is not installed, items proceed without flat lays."""
    from agent.tools import _display_product

    items = [{"title": "Hoodie", "image_url": "https://img/h.jpg", "product_id": "p1"}]

    # Setting a module to None in sys.modules causes ImportError on import
    with patch.dict(sys.modules, {"services.gemini_flatlay": None}):
        result = await _display_product({"items": items})

    assert result["displayed"] == 1
    assert result["frontend_payload"]["type"] == "display_product"
    assert result["items"][0].get("cleaned_image_url") is None


@pytest.mark.asyncio
async def test_display_product_gemini_api_failure_non_fatal():
    """When Gemini API fails, items proceed without flat lays."""
    from agent.tools import _display_product

    items = [{"title": "Jacket", "image_url": "https://img/jk.jpg", "product_id": "p1"}]

    fake_module = types.ModuleType("services.gemini_flatlay")
    fake_module.generate_flat_lays_batch = AsyncMock(
        side_effect=Exception("Gemini API rate limit exceeded")
    )

    with patch.dict(sys.modules, {"services.gemini_flatlay": fake_module}):
        result = await _display_product({"items": items})

    assert result["displayed"] == 1
    assert result["frontend_payload"]["type"] == "display_product"
    assert result["items"][0].get("cleaned_image_url") is None


@pytest.mark.asyncio
async def test_display_product_empty_returns_error():
    from agent.tools import _display_product

    result = await _display_product({"items": []})

    assert "error" in result
    assert result["displayed"] == 0
