# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mirrorless is an AI-powered smart mirror. Users onboard via phone (Google OAuth), their purchase history is scraped from Gmail, and AI stylist "Mira" gives personalized outfit recommendations overlaid on their body in real-time via a two-way mirror display.

## Architecture

- **Frontend (Next.js)**: Mirror display (full-screen Chrome on TV), phone UI (onboarding + dashboard), deployed on Vercel
- **Backend (Python FastAPI)**: Agent orchestrator, Gmail scraping, Serper.dev integration, MCP server, deployed on Render
- **Database**: Neon Postgres
- **Real-time**: Socket.io connecting mirror display, phone, and backend

## Key Technical Decisions

- **AI Agent**: Custom event-driven orchestrator calling Claude API directly (NOT Claude Agents SDK). Events (voice, gestures, pose) are batched and sent to Claude.
- **Claude Model**: Haiku 4.5 via Anthropic API with OAuth setup token + beta headers
- **Voice**: Deepgram streaming STT (input) → ElevenLabs TTS via backend proxy `/api/tts/speak` (output)
- **Avatar**: Memoji video loops (idle/thinking/talking/happy/excited/concerned) + 13 scripted response videos with baked-in audio. Scripted matching restricted to first 80 chars of response with keyword threshold 8. After scripted video plays, remaining text drains via TTS.
- **Body tracking**: MediaPipe BlazePose (pose) + MediaPipe Hands (gestures) in browser
- **Clothing overlay**: 2D affine transforms based on pose landmarks. Fallback: side-by-side display
- **Clothing data**: Serper.dev Google Shopping API (not SerpAPI)
- **Scraping strategy**: Fast parallel pass (~15s) for immediate agent context, background deep scrape async
- **Database connection**: Dual-mode setup - asyncpg pool (production on Render) or Neon serverless HTTP (local dev when port 5432 blocked)

## Voice & TTS Pipeline

Mira's voice flows through a multi-stage pipeline from Claude's streaming output to audio playback:

1. **Claude streaming** (`backend/agent/orchestrator.py`): `_call_claude()` streams via Anthropic async API. Each `content_block_delta` is emitted as a `mira_speech` Socket.io event with `{text, is_chunk: true}`. An empty event with `is_chunk: false` signals end-of-message.

2. **Frontend accumulation** (`frontend/src/app/mirror/page.tsx`): Chunks accumulate in `responseAccumulatorRef` until end-of-message, then the full text is processed.

3. **Scripted response check** (`frontend/src/lib/scripted-responses.ts`): 13 pre-recorded Memoji videos with baked-in audio (e.g., "okay i love that", "ew that's gross"). Two-pass matching: exact phrase `includes()`, then keyword scoring (threshold ≥ 4). If matched, plays the video directly — bypasses TTS entirely.

4. **Sentence buffering** (`frontend/src/lib/sentence-buffer.ts`): For non-scripted responses, splits text on `.!?` + space boundaries. Negative lookbehind regex `(?<!\d)(?<!\.)` avoids false splits on decimals (`$29.99`) and ellipsis (`...`).

5. **Speech queue** (`frontend/src/hooks/useMemojiAvatar.ts`): FIFO queue processes one sentence at a time. Avatar transitions: `idle` → `talking` → `idle`. Recursive `processQueue()` after each sentence completes.

6. **TTS client** (`frontend/src/lib/elevenlabs-tts.ts`): POSTs sentence to backend proxy `/api/tts/speak`. Receives audio/mpeg blob, plays via HTMLAudioElement. Falls back to browser `SpeechSynthesis` if proxy fails.

7. **Backend TTS proxy** (`backend/routers/tts.py`): Calls ElevenLabs API with `eleven_multilingual_v2` model, voice ID `EXAVITQu4vr4xnSDxMaL` (Sarah). Keeps API key server-side. Returns `StreamingResponse` audio/mpeg.

**STT input** (`frontend/src/hooks/useDeepgramSTT.ts`): WebSocket connection to Deepgram, `nova-2` model, mic audio converted to Int16 PCM, `utterance_end_ms=1500`. Transcripts are queued while avatar is speaking, sent when idle.

**Avatar states** (`frontend/src/lib/memoji-avatar.ts`): 6 muted looping videos (`idle`, `thinking`, `talking`, `happy`, `excited`, `concerned`) + 13 unmuted scripted one-shot videos. Happy/excited auto-revert to idle after 5s.

## Build & Run Commands

### Frontend (Next.js)
```
cd frontend
npm install
npm run dev        # Development server
npm run build      # Production build
npm run lint       # ESLint
```

### Backend (Python FastAPI)
```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload              # Development server
pytest                                 # Run all tests (must run from backend/)
pytest tests/test_database.py         # Single test file
python services/serper_search.py "mens jacket"  # CLI tool for testing Serper API
```

### Deploy
```
vercel --prod                           # Frontend to Vercel
# Backend deploys via Render dashboard or render.yaml
```

## Project Structure

```
frontend/           # Next.js app (mirror display + phone UI)
  src/
    app/
      mirror/       # Full-screen mirror display page
      phone/        # Phone onboarding + dashboard
    lib/            # Shared utilities
      elevenlabs-tts.ts    # TTS client (backend proxy + browser fallback)
      sentence-buffer.ts   # Streaming text → sentence splitter
      scripted-responses.ts # Phrase matching for pre-recorded videos
      memoji-avatar.ts     # Avatar video state machine
      socket.ts            # Socket.io client
    hooks/
      useMemojiAvatar.ts   # Avatar + TTS queue orchestration
      useDeepgramSTT.ts    # Deepgram STT WebSocket hook
      useCamera.ts         # Camera access hook
      useGestureRecognizer.ts # MediaPipe hand gesture hook
    components/mirror/
      AvatarPiP.tsx        # Avatar picture-in-picture
      ProductCarousel.tsx  # Product recommendation display
      VoiceIndicator.tsx   # Interim transcript indicator
      ClothingCanvas.tsx   # Clothing overlay rendering
      PriceStrip.tsx       # Minimal price strip on mirror page
    __tests__/             # Vitest test suites
  public/avatar/           # Memoji video assets
    loops/                 # 6 looping state videos (muted)
    scripted/              # 13 pre-recorded response videos (with audio)
backend/            # Python FastAPI
  main.py           # FastAPI app entry + Socket.io server
  agent/            # Mira orchestrator, Claude API integration
    orchestrator.py # Event-driven agent orchestrator
    prompts.py      # Mira's personality prompt
    tools.py        # Agent tool definitions
  routers/
    tts.py          # ElevenLabs TTS proxy endpoint
    auth.py         # Authentication routes
    queue.py        # Queue management routes
    users.py        # User routes
  scraper/          # Gmail scraping, data extraction
  mcp_server/       # MCP server for Poke integration (not mcp/ — avoids PyPI conflict)
  models/           # Pydantic models, DB schemas
    database.py     # Dual-mode DB connection (asyncpg + Neon HTTP)
    schemas.py      # Pydantic request/response models
  services/         # Serper.dev, Deepgram integrations
    serper_search.py  # Serper.dev Shopping API (CLI + library)
  migrations/       # Raw SQL migration files
    001_initial_schema.sql
  tests/            # Pytest test suite
jenny/              # Standalone Mira prototype (vanilla JS, archived reference)
  src/              # 9 JS modules (avatar, TTS, scripted responses, Gemini vision)
  assets/           # Memoji PNGs, loop videos, scripted videos
  bundle.py         # Self-contained HTML bundler
```

## Environment Variables

### Frontend (.env.local)
- `NEXT_PUBLIC_SOCKET_URL` — Backend WebSocket URL
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID` — Google OAuth client ID

### Backend (.env)
- `DATABASE_URL` — Neon Postgres connection string (required)
- `SERPER_API_KEY` — Serper.dev API key (required, see .env.example)
- `ANTHROPIC_API_KEY` — Claude API key (required)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — Google OAuth (planned)
- `DEEPGRAM_API_KEY` — Deepgram STT key (planned)
- `ELEVENLABS_API_KEY` — ElevenLabs TTS API key (required for voice output)
- `ELEVENLABS_VOICE_ID` — ElevenLabs voice ID (default: Sarah)

## Database Setup

The database uses Neon Postgres with a dual-mode connection strategy:
- **Production (Render)**: asyncpg connection pool via standard PostgreSQL port 5432
- **Local dev**: Neon serverless HTTP API when port 5432 is blocked (firewall/VPN)

### Running Migrations
Migrations are raw SQL files in `backend/migrations/`. Run them manually using:
```bash
psql $DATABASE_URL -f backend/migrations/001_initial_schema.sql
```

Or use the Neon SQL Editor in the dashboard.

## Current Implementation Status

**Completed**:
- Database schema and Neon Postgres integration
- Serper.dev Shopping API integration with CLI tool
- FastAPI backend with Socket.io real-time communication
- Next.js frontend with mirror/phone page structure
- MediaPipe integration for body/hand tracking
- Mira agent orchestrator (event-driven Claude API calls via `agent/orchestrator.py`)
- Memoji avatar with ElevenLabs TTS, scripted response videos, and per-sentence speech queue
- ElevenLabs TTS backend proxy (`backend/routers/tts.py`) with proper blob lifecycle management
- Deepgram streaming STT (`useDeepgramSTT` hook)
- SentenceBuffer for per-sentence TTS delivery
- Scripted response matching with TTS continuation for remaining text
- Mirror UI components: AvatarPiP, ProductCarousel, VoiceIndicator
- MCP server for Poke integration (`backend/mcp_server/`)

**In Progress / Planned**:
- Gmail OAuth and scraping pipeline
- Clothing overlay rendering
- Orb-based avatar replacement (replacing Memoji video loops with animated orb)

## Conventions

- Frontend uses TypeScript, backend uses Python 3.11+
- Socket.io events use snake_case: `outfit_changed`, `gesture_detected`, `session_started`
- All Claude API calls go through `backend/agent/orchestrator.py` — never call Claude directly from frontend
- Mira's personality prompt lives in `backend/agent/prompts.py`
- Database migrations via raw SQL files in `backend/migrations/`
