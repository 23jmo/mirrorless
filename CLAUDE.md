# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mirrorless is an AI-powered smart mirror. Users interact via **Poke** (an AI assistant in iMessage/Telegram/SMS) which connects to our tools via MCP. Poke knows the user's purchase history, calendar, and preferences through its own integrations. Our tools let Poke **search for clothes** and **display items on the user's physical mirror**.

## Build & Run Commands

### Frontend (Next.js 15 + React 19 + TypeScript)

```bash
cd frontend
npm install
npm run dev          # Dev server on :3000
npm run build        # Production build (also type-checks)
npm run lint         # ESLint
npm run test         # Vitest (single run)
npm run test:watch   # Vitest (watch mode)
```

### Backend (Python 3.11+ / FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload        # Dev server on :8000
pytest                           # All tests
pytest tests/test_auth.py -v     # Single test file
```

### MCP Server (FastMCP)

```bash
cd backend
pip install -r mcp_server/requirements.txt
uvicorn mcp_server.server:app --host 0.0.0.0 --port 8001  # MCP server on :8001
pytest mcp_server/tests/ -v                                 # MCP tests
```

### Deploy

```bash
vercel --prod          # Frontend to Vercel
# Backend + MCP server deploy via Render dashboard
```

## Architecture

- **Frontend (Next.js on Vercel)**: Mirror display (full-screen Chrome on TV) and phone UI
- **Backend (FastAPI on Render)**: Socket.io bridge, auth, queue, mirror endpoints
- **MCP Server (FastMCP on Render)**: Exposes 5 tools to Poke via MCP protocol
- **Database**: Neon Postgres. Schema in `backend/migrations/`
- **Real-time**: Socket.io connecting mirror display and backend
- **AI Brain**: **Poke** (external) — connects to our MCP server, handles all AI logic

### Data flow

```
User texts Poke → Poke calls our MCP tools → MCP server → Backend HTTP → Socket.io → Mirror display
```

Specifically:
```
Poke → search_clothing (MCP) → Serper API → results to Poke only
Poke → present_items (MCP) → POST /api/mirror/present → Socket.io emit → Mirror shows cards
Poke → send_to_mirror (MCP) → POST /api/mirror/text → Socket.io emit → Mirror shows text + TTS
```

### MCP Server (`backend/mcp_server/`)

Five tools exposed to Poke:

| Tool | Purpose | Backend Endpoint |
|------|---------|-----------------|
| `search_clothing` | Search Serper API for clothes | None (returns to Poke) |
| `present_items` | Show clothing cards on mirror | `POST /api/mirror/present` |
| `send_to_mirror` | Show text on mirror (+ TTS) | `POST /api/mirror/text` |
| `get_past_sessions` | Query previous sessions | `GET /api/mirror/sessions/{id}` |
| `save_session` | Save session summary | `POST /api/mirror/sessions` |

Key files:
- **`server.py`** — FastMCP instance with tool definitions and instructions
- **`shopping.py`** — Serper.dev Shopping API client
- **`mirror.py`** — HTTP client for backend bridge endpoints
- **`render.yaml`** — Render deployment config

### Mirror Bridge (`backend/routers/mirror.py`)

REST endpoints that translate HTTP requests from the MCP server into Socket.io emissions. Each mirror joins a room `mirror:<mirror_id>` at startup. The MCP server is stateless — it calls these endpoints to push data.

### Database access pattern

Backend uses `NeonHTTPClient` (in `models/database.py`) — a thin wrapper around Neon's serverless HTTP API on port 443. Each endpoint creates a client, uses it, closes it. All queries use `$1, $2` parameterized placeholders.

## Key Technical Decisions

- **AI Brain**: **Poke** (external MCP host) — NOT a custom orchestrator. We expose tools via MCP; Poke handles conversation, personality, user context, and tool orchestration.
- **Mirror linking**: Permanent mirror_id (e.g. "MIRROR-A1") configured at setup. User tells Poke their mirror_id once; Poke remembers it. No user registration needed.
- **Stateless MCP server**: Each tool call is independent. Mirror bridge uses HTTP to reach the stateful Socket.io backend.
- **Google OAuth**: Authorization code flow for user auth (kept for phone onboarding).
- **No JWT/sessions**: `user_id` (UUID) is the session identifier, stored in React state.
- **Gesture detection**: MediaPipe Hands in browser → `gesture-classifier.ts`
- **Clothing data**: Serper.dev Shopping API (`POST https://google.serper.dev/shopping`)
- **Voice pipeline**: Deepgram streaming STT (input) → HeyGen LiveAvatar API (output)
- **Frontend styling**: Inline styles (no CSS framework)

## API Endpoints (Backend)

| Method | Path                            | Purpose                                    |
| ------ | ------------------------------- | ------------------------------------------ |
| POST   | `/auth/google`                  | Exchange Google OAuth code → upsert user   |
| POST   | `/auth/profile`                 | Update user name + phone                   |
| POST   | `/queue/join`                   | Idempotent queue join, returns position    |
| GET    | `/queue/status/{user_id}`       | Poll queue position + total_ahead          |
| GET    | `/users/{user_id}`              | Fetch user profile                         |
| POST   | `/api/mirror/present`           | Push clothing items to mirror (Socket.io)  |
| POST   | `/api/mirror/text`              | Push text to mirror (Socket.io + TTS)      |
| GET    | `/api/mirror/sessions/{mirror}` | Get past sessions for a mirror             |
| POST   | `/api/mirror/sessions`          | Save a session record                      |
| GET    | `/api/mirror/status/{mirror}`   | Check if a mirror is connected             |
| GET    | `/health`                       | Health check                               |

## Environment Variables

### Frontend `.env.local`

- `NEXT_PUBLIC_API_URL` — Backend REST URL (e.g. `http://localhost:8000`)
- `NEXT_PUBLIC_SOCKET_URL` — Backend WebSocket URL
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID` — Google OAuth client ID
- `NEXT_PUBLIC_MIRROR_ID` — This mirror's permanent ID (e.g. `MIRROR-A1`)

### Backend `.env`

- `DATABASE_URL` — Neon Postgres connection string
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — Google OAuth
- `SERPER_API_KEY` — Serper.dev shopping API key
- `DEEPGRAM_API_KEY` — Deepgram STT key
- `HEYGEN_API_KEY` — HeyGen avatar API key

### MCP Server `.env`

- `SERPER_API_KEY` — Serper.dev shopping API key
- `BACKEND_URL` — Backend REST URL (e.g. `https://mirrorless-backend.onrender.com`)
- `MCP_PORT` — Port for MCP server (default 8001)

## Conventions

- Frontend: TypeScript strict mode, path alias `@/*` → `./src/*`
- Backend: Python 3.11+, Pydantic models in `models/schemas.py`
- Socket.io events: snake_case (`tool_result`, `mirror_text`, `join_room`)
- MCP tools are the only interface for AI interaction — no direct Claude API calls
- Database migrations: raw SQL in `backend/migrations/`
- MCP tool tests use mocked HTTP (no live dependencies)
- Backend endpoint tests use mocked Socket.io and DB
- Frontend tests use Vitest + jsdom + @testing-library/react
