from uuid import UUID

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import socketio

from routers import auth, queue, users, heygen
from scraper.routes import router as scraper_router
from judges.routes import router as judges_router

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

# Map socket IDs to user IDs for disconnect cleanup
_sid_to_user: dict[str, str] = {}

app = FastAPI(title="Mirrorless API", version="0.1.0")

# CORS on FastAPI only — Socket.io handles its own CORS via cors_allowed_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(queue.router)
app.include_router(users.router)
app.include_router(scraper_router)
app.include_router(judges_router)
app.include_router(heygen.router)

# Make sio accessible to routes
app.state.sio = sio


@app.get("/health")
async def health():
    return {"status": "ok"}


# --- Socket.io events ---


@sio.event
async def connect(sid, environ):
    print(f"[socket] Client connected: {sid}")


@sio.event
async def join_room(sid, data):
    """Client joins a user-specific room for targeted events.

    Supports both mirror_id (mirror display) and user_id (phone/Poke).
    """
    user_id = data.get("user_id")
    mirror_id = data.get("mirror_id")
    room = mirror_id or user_id
    if room:
        await sio.enter_room(sid, room)
        _sid_to_user[sid] = room
        print(f"[socket] {sid} joined room {room}")


@sio.event
async def disconnect(sid):
    print(f"[socket] Client disconnected: {sid}")
    _sid_to_user.pop(sid, None)


def _is_valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


@sio.event
async def start_session(sid, data):
    """Signal that a session is starting.

    The actual AI orchestration is handled by Poke (external MCP host).
    This just notifies connected clients that the session is active.
    """
    user_id = data.get("user_id")
    if not user_id:
        return

    if not _is_valid_uuid(user_id):
        print(f"[session] Invalid UUID from {sid}: {user_id}")
        await sio.emit(
            "session_error",
            {"error": "Invalid user ID: must be a valid UUID"},
            to=sid,
        )
        return

    print(f"[session] Starting session for user {user_id}")
    await sio.emit("session_active", {"user_id": user_id}, room=user_id)


@sio.event
async def mirror_event(sid, data):
    """Forward events from the mirror to the user's room (picked up by Poke)."""
    user_id = data.get("user_id")
    if not user_id:
        return
    await sio.emit("mirror_event", data, room=user_id, skip_sid=sid)


@sio.event
async def end_session(sid, data):
    """End a session — notify connected clients."""
    user_id = data.get("user_id")
    if not user_id:
        return
    print(f"[session] Ending session for user {user_id}")
    await sio.emit("session_ended", {"user_id": user_id}, room=user_id)


# Wrap FastAPI with Socket.io — no outer CORS wrapper needed
# (Socket.io has its own CORS via cors_allowed_origins, FastAPI has its own middleware)
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
