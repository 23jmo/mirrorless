# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mirrorless is an AI-powered smart mirror. Users onboard via phone (Google OAuth), their purchase history is scraped from Gmail, and AI stylist "Mira" gives personalized outfit recommendations overlaid on their body in real-time via a two-way mirror display.

## Architecture

- **Frontend (Next.js)**: Mirror display (full-screen Chrome on TV), phone UI (onboarding + dashboard), deployed on Vercel
- **Backend (Python FastAPI)**: Agent orchestrator, Gmail scraping, SerpAPI integration, MCP server, deployed on Render
- **Database**: Neon Postgres
- **Real-time**: Socket.io connecting mirror display, phone, and backend

## Key Technical Decisions

- **AI Agent**: Custom event-driven orchestrator calling Claude API directly (NOT Claude Agents SDK). Events (voice, gestures, pose) are batched and sent to Claude.
- **Claude Model**: Haiku 4.5 via Anthropic API with OAuth setup token + beta headers
- **Voice**: Deepgram streaming STT (input) → HeyGen LiveAvatar API (output)
- **Body tracking**: MediaPipe BlazePose (pose) + MediaPipe Hands (gestures) in browser
- **Clothing overlay**: 2D affine transforms based on pose landmarks. Fallback: side-by-side display
- **Clothing data**: SerpAPI / Google Shopping API
- **Scraping strategy**: Fast parallel pass (~15s) for immediate agent context, background deep scrape async

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
uvicorn main:app --reload    # Development server
pytest                       # Run tests
pytest tests/test_scraper.py # Single test file
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
      api/          # Next.js API routes (Socket.io, etc.)
    components/
      mirror/       # Mirror-specific components (overlay, Mira avatar)
      phone/        # Phone UI components
    lib/            # Shared utilities, Socket.io client
backend/            # Python FastAPI
  main.py           # FastAPI app entry
  agent/            # Mira orchestrator, Claude API integration
  scraper/          # Gmail scraping, data extraction
  mcp/              # MCP server for Poke integration
  models/           # Pydantic models, DB schemas
  services/         # SerpAPI, Deepgram, HeyGen integrations
```

## Environment Variables

### Frontend (.env.local)
- `NEXT_PUBLIC_SOCKET_URL` — Backend WebSocket URL
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID` — Google OAuth client ID

### Backend (.env)
- `DATABASE_URL` — Neon Postgres connection string
- `ANTHROPIC_API_KEY` — Claude API key
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — Google OAuth
- `SERPAPI_KEY` — SerpAPI key
- `DEEPGRAM_API_KEY` — Deepgram STT key
- `HEYGEN_API_KEY` — HeyGen avatar API key

## Conventions

- Frontend uses TypeScript, backend uses Python 3.11+
- Socket.io events use snake_case: `outfit_changed`, `gesture_detected`, `session_started`
- All Claude API calls go through `backend/agent/orchestrator.py` — never call Claude directly from frontend
- Mira's personality prompt lives in `backend/agent/prompts.py`
- Database migrations via raw SQL files in `backend/migrations/`
