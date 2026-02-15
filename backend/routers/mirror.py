"""Mirror bridge endpoints — translate HTTP requests into Socket.io emissions.

The MCP server calls these endpoints to push data to physical mirror displays.
Each mirror joins a Socket.io room named "mirror:<mirror_id>" at startup.
"""

import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from models.database import NeonHTTPClient

POKE_WEBHOOK_URL = "https://poke.com/api/v1/inbound-sms/webhook"
POKE_API_KEY = os.getenv("POKE_API_KEY", "")

router = APIRouter(prefix="/api/mirror", tags=["mirror"])


# --- Request/Response schemas ---


class PresentItem(BaseModel):
    title: str
    price: str
    image_url: str
    link: str
    source: str
    product_id: str | None = None
    rating: float | None = None
    rating_count: int | None = None


class PresentItemsRequest(BaseModel):
    mirror_id: str
    items: list[PresentItem] = Field(..., min_length=1, max_length=5)


class MirrorTextRequest(BaseModel):
    mirror_id: str
    text: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    mirror_id: str
    text: str = Field(..., min_length=1)


class SessionItem(BaseModel):
    title: str
    price: str | None = None
    image_url: str | None = None
    link: str | None = None
    source: str | None = None
    reaction: str | None = None  # "liked", "disliked", "skipped"


class SaveSessionRequest(BaseModel):
    mirror_id: str
    summary: str
    items_shown: list[SessionItem] = []
    reactions: dict = {}  # e.g. {"likes": 2, "dislikes": 1, "items_shown": 5}


# --- Endpoints ---


@router.post("/present")
async def present_items(req: PresentItemsRequest, request: Request):
    """Push clothing items to a mirror display via Socket.io."""
    sio = request.app.state.sio
    room = f"mirror:{req.mirror_id}"

    payload = {
        "type": "clothing_results",
        "items": [item.model_dump() for item in req.items],
    }
    await sio.emit("tool_result", payload, room=room)

    return {"ok": True, "presented": len(req.items), "mirror_id": req.mirror_id}


@router.post("/text")
async def mirror_text(req: MirrorTextRequest, request: Request):
    """Push text (+ TTS trigger) to a mirror display via Socket.io."""
    sio = request.app.state.sio
    room = f"mirror:{req.mirror_id}"

    await sio.emit("mirror_text", {"text": req.text}, room=room)

    return {"ok": True, "mirror_id": req.mirror_id}


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    """Relay a user message to Poke via its inbound webhook, then confirm to mirror."""
    sio = request.app.state.sio
    room = f"mirror:{req.mirror_id}"

    # Forward to Poke
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            POKE_WEBHOOK_URL,
            json={"message": req.text},
            headers={"Authorization": f"Bearer {POKE_API_KEY}"},
        )
        resp.raise_for_status()

    # Confirm to mirror that the message was sent
    await sio.emit("chat_sent", {"text": req.text}, room=room)

    return {"ok": True, "mirror_id": req.mirror_id}


@router.get("/sessions/{mirror_id}")
async def get_sessions(mirror_id: str, limit: int = 5):
    """Return past shopping sessions for a mirror."""
    db = NeonHTTPClient()
    try:
        sessions = await db.execute(
            """
            SELECT s.id, s.started_at, s.ended_at, s.status
            FROM sessions s
            WHERE s.mirror_id = $1
            ORDER BY s.started_at DESC
            LIMIT $2
            """,
            [mirror_id, limit],
        )

        results = []
        for session in sessions:
            # Fetch outfits for this session
            outfits = await db.execute(
                """
                SELECT outfit_data, reaction
                FROM session_outfits
                WHERE session_id = $1
                """,
                [session["id"]],
            )

            results.append({
                "session_id": session["id"],
                "started_at": str(session["started_at"]) if session.get("started_at") else None,
                "ended_at": str(session["ended_at"]) if session.get("ended_at") else None,
                "status": session.get("status"),
                "items": [
                    {
                        "data": o.get("outfit_data", {}),
                        "reaction": o.get("reaction"),
                    }
                    for o in outfits
                ],
            })

        return {"sessions": results, "mirror_id": mirror_id}
    finally:
        await db.close()


@router.post("/sessions")
async def save_session(req: SaveSessionRequest):
    """Save a shopping session record."""
    db = NeonHTTPClient()
    try:
        # Create session row — use a placeholder user_id (null-safe)
        # Since sessions table requires user_id (FK), we need to handle this.
        # For now, create a session with mirror_id and minimal data.
        # The sessions table has user_id NOT NULL, so we'll store mirror_id
        # and use a default user for mirror-only sessions.
        session_rows = await db.execute(
            """
            INSERT INTO sessions (mirror_id, status, ended_at)
            VALUES ($1, 'completed', $2)
            RETURNING id
            """,
            [req.mirror_id, datetime.now(timezone.utc).isoformat()],
        )

        if not session_rows:
            return {"ok": False, "error": "Failed to create session"}

        session_id = session_rows[0]["id"]

        # Save each item as a session_outfit row
        for item in req.items_shown:
            await db.execute(
                """
                INSERT INTO session_outfits (session_id, outfit_data, reaction)
                VALUES ($1, $2, $3)
                """,
                [
                    session_id,
                    {
                        "title": item.title,
                        "price": item.price,
                        "image_url": item.image_url,
                        "link": item.link,
                        "source": item.source,
                    },
                    item.reaction,
                ],
            )

        # Save summary as a special session_outfit with reaction='summary'
        if req.summary:
            await db.execute(
                """
                INSERT INTO session_outfits (session_id, outfit_data, reaction)
                VALUES ($1, $2, 'summary')
                """,
                [session_id, {"summary": req.summary, "reactions": req.reactions}],
            )

        return {"ok": True, "session_id": session_id, "mirror_id": req.mirror_id}
    finally:
        await db.close()


@router.get("/status/{mirror_id}")
async def mirror_status(mirror_id: str, request: Request):
    """Check if a mirror is currently connected via Socket.io."""
    sio = request.app.state.sio
    room = f"mirror:{mirror_id}"

    # Check if the room has any members
    # get_participants is a regular generator in python-socketio 5.x
    connected = any(True for _ in sio.manager.get_participants("/", room))

    return {"connected": connected, "mirror_id": mirror_id}
