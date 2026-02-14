from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import socketio

from routers import auth, queue, users
from routers.images import router as images_router
from scraper.routes import router as scraper_router

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=[])

app = FastAPI(title="Mirrorless API", version="0.1.0")

app.include_router(auth.router)
app.include_router(queue.router)
app.include_router(users.router)
app.include_router(scraper_router)
app.include_router(images_router)

# Make sio accessible to routes
app.state.sio = sio


@app.get("/health")
async def health():
    return {"status": "ok"}


@sio.event
async def connect(sid, environ):
    print(f"[socket] Client connected: {sid}")


@sio.event
async def join_room(sid, data):
    """Client joins a user-specific room for targeted events."""
    user_id = data.get("user_id")
    if user_id:
        await sio.enter_room(sid, user_id)
        print(f"[socket] {sid} joined room {user_id}")


@sio.event
async def disconnect(sid):
    print(f"[socket] Client disconnected: {sid}")


@sio.event
async def request_snapshot(sid, data):
    """Backend requests a camera snapshot from the mirror."""
    user_id = data.get("user_id")
    if user_id:
        await sio.emit("request_snapshot", {"user_id": user_id}, room=user_id)
        print(f"[socket] Requested snapshot from mirror for user {user_id}")


@sio.event
async def camera_snapshot(sid, data):
    """Mirror sends back a camera snapshot."""
    user_id = data.get("user_id")
    image_base64 = data.get("image_base64")
    print(f"[socket] Received snapshot from {user_id}: {len(image_base64) if image_base64 else 0} bytes")
    # Store in memory for agent to consume (will be used by orchestrator)


@sio.event
async def session_ready(sid, data):
    """Mirror display reports it's loaded and ready."""
    user_id = data.get("user_id")
    if user_id:
        await sio.enter_room(sid, f"mirror_{user_id}")
        print(f"[socket] Mirror ready for user {user_id}")


# Wrap FastAPI with Socket.io, then wrap everything with CORS
_asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)
socket_app = CORSMiddleware(
    _asgi_app,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
