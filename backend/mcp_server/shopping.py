"""Serper.dev Shopping API client for clothing search.

Extracted from agent/tools.py for standalone use in the MCP server.
"""

import os
import re

import httpx
from dotenv import load_dotenv

load_dotenv()

SERPER_SHOPPING_URL = "https://google.serper.dev/shopping"


def _parse_price(price_str: str) -> float | None:
    """Extract numeric price from string like '$595.00'."""
    match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
    return float(match.group()) if match else None


async def search_serper(query: str, num_results: int = 8) -> dict:
    """Search Serper.dev Shopping API and return normalized results.

    Args:
        query: Detailed shopping search query (e.g. "mens black minimalist sneakers under $150").
        num_results: Number of results to return (default 8, max 20).

    Returns:
        Dict with "results" list of product dicts, or "error" key on failure.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return {"error": "SERPER_API_KEY not configured", "results": []}

    num_results = min(num_results, 20)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                SERPER_SHOPPING_URL,
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": num_results},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"Shopping search failed: HTTP {e.response.status_code}", "results": []}
    except Exception as e:
        return {"error": f"Shopping search failed: {str(e)}", "results": []}

    results = []
    for item in data.get("shopping", []):
        results.append({
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "price": item.get("price", ""),
            "price_numeric": _parse_price(item.get("price", "")),
            "image_url": item.get("imageUrl", ""),
            "link": item.get("link", ""),
            "product_id": item.get("productId", ""),
            "rating": item.get("rating"),
            "rating_count": item.get("ratingCount"),
        })

    return {"results": results}
