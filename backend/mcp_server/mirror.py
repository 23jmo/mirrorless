"""Mirror bridge client — calls backend HTTP endpoints to push data to mirrors.

These functions are called by the MCP tools in server.py. They handle the HTTP
communication with the FastAPI backend, which translates into Socket.io emissions.
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


async def do_present_items(mirror_id: str, items: list[dict]) -> dict:
    """Push clothing items to a mirror display via the backend bridge."""
    if not items:
        return {"error": "No items provided", "presented": 0}

    items = items[:5]

    required_fields = {"title", "price", "image_url", "link", "source"}
    for item in items:
        missing = required_fields - set(item.keys())
        if missing:
            return {"error": f"Item missing required fields: {missing}"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/mirror/present",
                json={"mirror_id": mirror_id, "items": items},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": f"Failed to present items: {str(e)}"}


async def do_send_to_mirror(mirror_id: str, text: str) -> dict:
    """Send text to a mirror display via the backend bridge."""
    if not text.strip():
        return {"error": "Text cannot be empty"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/mirror/text",
                json={"mirror_id": mirror_id, "text": text},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": f"Failed to send to mirror: {str(e)}"}


async def do_get_past_sessions(mirror_id: str, limit: int = 5) -> dict:
    """Retrieve past shopping sessions from the backend."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BACKEND_URL}/api/mirror/sessions/{mirror_id}",
                params={"limit": limit},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": f"Failed to get sessions: {str(e)}"}


async def do_save_session(
    mirror_id: str,
    summary: str,
    items_shown: list[dict] | None = None,
    reactions: dict | None = None,
) -> dict:
    """Save a shopping session via the backend."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/mirror/sessions",
                json={
                    "mirror_id": mirror_id,
                    "summary": summary,
                    "items_shown": items_shown or [],
                    "reactions": reactions or {},
                },
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"error": f"Failed to save session: {str(e)}"}
