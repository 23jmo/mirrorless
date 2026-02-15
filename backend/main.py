from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import socketio

from routers import auth, queue, users, heygen
from routers.mirror import router as mirror_router
from judges.routes import router as judges_router

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

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
app.include_router(judges_router)
app.include_router(heygen.router)
app.include_router(mirror_router)

# Make sio accessible to routes (mirror bridge endpoints need it)
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
    """Client joins a mirror-specific or user-specific room."""
    mirror_id = data.get("mirror_id")
    user_id = data.get("user_id")

    if mirror_id:
        room = f"mirror:{mirror_id}"
        await sio.enter_room(sid, room)
        print(f"[socket] {sid} joined mirror room {room}")

    if user_id:
        await sio.enter_room(sid, user_id)
        print(f"[socket] {sid} joined room {user_id}")


@sio.event
async def disconnect(sid):
    print(f"[socket] Client disconnected: {sid}")


# Wrap FastAPI with Socket.io — no outer CORS wrapper needed
# (Socket.io has its own CORS via cors_allowed_origins, FastAPI has its own middleware)
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
