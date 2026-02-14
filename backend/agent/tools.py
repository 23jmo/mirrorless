"""Tool definitions for Mira agent — Claude tool_use format."""

import os
import re

import httpx
from dotenv import load_dotenv

from models.database import NeonHTTPClient
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
    {
        "name": "search_purchases",
        "description": (
            "Search the user's full purchase history stored in the database. Use this to look up "
            "specific purchases by brand, category, price range, or date range. This searches ALL "
            "purchases ever scraped — not just the ones in your context. Use when the user asks "
            "about past purchases, a specific brand, or when you want to reference items from "
            "their historical purchases."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text search against brand and item name, e.g. 'leather jacket' or 'running shoes'",
                },
                "brand": {
                    "type": "string",
                    "description": "Exact brand filter, e.g. 'Nike' or 'Zara'",
                },
                "category": {
                    "type": "string",
                    "description": "Exact category filter, e.g. 'shoes' or 'tops'",
                },
                "min_price": {
                    "type": "number",
                    "description": "Minimum price filter",
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum price filter",
                },
                "date_from": {
                    "type": "string",
                    "description": "Start date filter (YYYY-MM-DD format)",
                },
                "date_to": {
                    "type": "string",
                    "description": "End date filter (YYYY-MM-DD format)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 20, max 50)",
                    "default": 20,
                },
            },
            "required": [],
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
    elif tool_name == "search_purchases":
        return await _search_purchases(tool_input, user_context)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


async def _search_clothing(tool_input: dict) -> dict:
    """Search Serper.dev Shopping API."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return {"error": "SERPER_API_KEY not configured", "results": []}

    query = tool_input["query"]
    num_results = min(tool_input.get("num_results", 10), 40)

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
    except Exception as e:
        return {"error": f"Shopping search failed: {str(e)}", "results": []}

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


async def _search_purchases(tool_input: dict, user_context: dict) -> dict:
    """Search the user's full purchase history in the database."""
    user_id = user_context.get("user_id")
    if not user_id:
        return {"error": "No user_id available", "results": []}

    # Build dynamic WHERE clause with parameterized inputs
    conditions = ["user_id = $1"]
    params: list = [user_id]
    param_idx = 2

    query_text = tool_input.get("query")
    if query_text:
        conditions.append(f"(brand ILIKE ${param_idx} OR item_name ILIKE ${param_idx})")
        params.append(f"%{query_text}%")
        param_idx += 1

    brand = tool_input.get("brand")
    if brand:
        conditions.append(f"LOWER(brand) = LOWER(${param_idx})")
        params.append(brand)
        param_idx += 1

    category = tool_input.get("category")
    if category:
        conditions.append(f"LOWER(category) = LOWER(${param_idx})")
        params.append(category)
        param_idx += 1

    min_price = tool_input.get("min_price")
    if min_price is not None:
        conditions.append(f"price >= ${param_idx}")
        params.append(min_price)
        param_idx += 1

    max_price = tool_input.get("max_price")
    if max_price is not None:
        conditions.append(f"price <= ${param_idx}")
        params.append(max_price)
        param_idx += 1

    date_from = tool_input.get("date_from")
    if date_from:
        conditions.append(f"date >= ${param_idx}::date")
        params.append(date_from)
        param_idx += 1

    date_to = tool_input.get("date_to")
    if date_to:
        conditions.append(f"date <= ${param_idx}::date")
        params.append(date_to)
        param_idx += 1

    limit = min(tool_input.get("limit", 20), 50)
    where_clause = " AND ".join(conditions)

    try:
        db = NeonHTTPClient()
        try:
            # Get matching purchases
            rows = await db.execute(
                f"SELECT brand, item_name, category, price, date "
                f"FROM purchases WHERE {where_clause} "
                f"ORDER BY date DESC LIMIT {limit}",
                params,
            )

            # Get total matching count (for pagination context)
            count_rows = await db.execute(
                f"SELECT COUNT(*) as total FROM purchases WHERE {where_clause}",
                params,
            )
        finally:
            await db.close()

        results = [
            {
                "brand": r.get("brand", ""),
                "item_name": r.get("item_name", ""),
                "category": r.get("category"),
                "price": float(r["price"]) if r.get("price") else None,
                "date": str(r["date"]) if r.get("date") else None,
            }
            for r in rows
        ]

        total_matching = int(count_rows[0]["total"]) if count_rows else len(results)

        return {
            "results": results,
            "total_matching": total_matching,
            "showing": len(results),
        }
    except Exception as e:
        return {"error": f"Purchase search failed: {str(e)}", "results": []}
