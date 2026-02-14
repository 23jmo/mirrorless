"""Tool definitions for Mira agent — Claude tool_use format."""

import os
import re

import httpx
from dotenv import load_dotenv

from scraper.gmail_auth import build_gmail_service
from scraper.gmail_fetch import search_emails, get_message_content

load_dotenv()

SERPER_SHOPPING_URL = "https://google.serper.dev/shopping"

# Claude tool definitions
TOOL_DEFINITIONS = [
    {
        "name": "search_clothing",
        "description": (
            "Search for clothing items using Google Shopping. Returns a list of products with "
            "title, price, image, retailer, rating, and buy link. Use this to find specific "
            "clothing items or browse categories. Craft your query to match what the user is "
            "looking for, informed by their style profile and the conversation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Shopping search query, e.g. 'black leather jacket men' or 'minimalist white sneakers women'",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 10, max 40)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_gmail",
        "description": (
            "Search the user's Gmail for specific information. Use this when the user mentions "
            "a specific purchase, brand, or item and you want to look up details. Returns email "
            "subjects and snippets matching the query. Do NOT use this for general profile building "
            "— that data is already in your context."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query, e.g. 'from:zara order confirmation' or 'subject:Nike receipt'",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max emails to return (default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
]


def _parse_price(price_str: str) -> float | None:
    """Extract numeric price from string like '$595.00'."""
    match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
    return float(match.group()) if match else None


async def execute_tool(tool_name: str, tool_input: dict, user_context: dict) -> dict:
    """Execute a tool call and return the result.

    Args:
        tool_name: Name of the tool to execute.
        tool_input: Input parameters from Claude.
        user_context: Dict with user-specific data (oauth_token, user_id, etc.)

    Returns:
        Dict with tool results and optional frontend_payload for parallel broadcast.
    """
    if tool_name == "search_clothing":
        return await _search_clothing(tool_input)
    elif tool_name == "search_gmail":
        return await _search_gmail(tool_input, user_context)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


async def _search_clothing(tool_input: dict) -> dict:
    """Search Serper.dev Shopping API."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return {"error": "SERPER_API_KEY not configured", "results": []}

    query = tool_input["query"]
    num_results = min(tool_input.get("num_results", 10), 40)

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

    results = []
    for item in data.get("shopping", []):
        results.append({
            "title": item["title"],
            "source": item["source"],
            "price": item["price"],
            "price_numeric": _parse_price(item["price"]),
            "image_url": item["imageUrl"],
            "link": item["link"],
            "product_id": item["productId"],
            "rating": item.get("rating"),
            "rating_count": item.get("ratingCount"),
        })

    return {
        "results": results,
        # Separate payload for frontend parallel broadcast via Socket.io
        "frontend_payload": {
            "type": "clothing_results",
            "query": query,
            "items": results,
        },
    }


async def _search_gmail(tool_input: dict, user_context: dict) -> dict:
    """Search user's Gmail."""
    token_data = user_context.get("oauth_token")
    if not token_data:
        return {"error": "No OAuth token available for this user", "results": []}

    query = tool_input["query"]
    max_results = min(tool_input.get("max_results", 5), 10)

    try:
        service = build_gmail_service(token_data)
        message_ids = search_emails(service, query=query, max_results=max_results)

        emails = []
        for msg_id in message_ids:
            content = get_message_content(service, msg_id)
            emails.append({
                "subject": content["subject"],
                "sender": content["sender"],
                "date": content["date"],
                "snippet": content["body"][:300] if content["body"] else "",
            })

        return {"results": emails}
    except Exception as e:
        return {"error": f"Gmail search failed: {str(e)}", "results": []}
