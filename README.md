# Mirrorless

An AI-powered smart mirror that gives personalized outfit recommendations overlaid on your body in real-time. Users onboard via phone (Google OAuth), their purchase history is scraped from Gmail, and AI stylist "Mira" delivers styling advice through a two-way mirror display.

## How It Works

1. **Scan** the QR code on the mirror with your phone
2. **Sign in** with Google, take a selfie, and fill out a quick style questionnaire
3. **Step up** to the mirror when it's your turn
4. **Talk to Mira** — she roasts your current outfit, searches for new pieces, and overlays clothing on your body in real-time
5. **React with gestures** — thumbs up/down to like or skip, swipe to browse outfits
6. **Get your picks** saved to your phone when the session ends

## Architecture

```
Phone (Next.js)  ──┐
                    ├── Socket.io ──▶  Backend (FastAPI + Python)
Mirror (Next.js) ──┘                      │
                                          ├── Claude API (Mira agent)
                                          ├── Deepgram (STT)
                                          ├── ElevenLabs (TTS)
                                          ├── Serper.dev (Google Shopping)
                                          ├── Gemini (flat lay generation)
                                          └── Neon Postgres (database)
```

- **Frontend**: Next.js app serving the mirror display (full-screen kiosk), phone UI (onboarding + dashboard), and admin dashboard. Deployed on Vercel.
- **Backend**: Python FastAPI with Socket.io for real-time communication. Hosts the Mira agent orchestrator, Gmail scraping, and an MCP server for external AI integrations. Deployed on Render.
- **Database**: Neon Postgres with dual-mode connections (asyncpg pool in production, Neon HTTP locally).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.11+, Socket.io |
| AI Agent | Claude (Anthropic API), custom event-driven orchestrator |
| Voice | Deepgram streaming STT, ElevenLabs streaming TTS |
| Avatar | Pre-recorded MP4 emotion loops (26 emotions) |
| Body Tracking | MediaPipe BlazePose + MediaPipe Hands |
| Clothing Data | Serper.dev Google Shopping API |
| Image Processing | Gemini (flat lays), rembg (background removal) |
| Database | Neon Postgres |
| Deployment | Vercel (frontend), Render (backend) |

## Setup

### Prerequisites

- Node.js 18+
- Python 3.11+
- A Neon Postgres database

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Environment Variables

**Frontend** (`.env.local`):
- `NEXT_PUBLIC_SOCKET_URL` — Backend WebSocket URL
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID` — Google OAuth client ID
- `NEXT_PUBLIC_PHONE_URL` — Phone onboarding URL (for QR code)

**Backend** (`.env`):
- `DATABASE_URL` — Neon Postgres connection string
- `ANTHROPIC_API_KEY` — Claude API key
- `SERPER_API_KEY` — Serper.dev API key
- `DEEPGRAM_API_KEY` — Deepgram STT key
- `ELEVENLABS_API_KEY` — ElevenLabs TTS key
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — Google OAuth

## Mirror Kiosk Flow

The mirror runs as a full-screen kiosk with four states:

1. **Attract** — QR code and branding, waiting for users to scan
2. **Waiting** — Shows "Up next: [name]" with a 2-minute auto-skip timeout
3. **Session** — Active AI stylist session with voice, gestures, and clothing overlay
4. **Recap** — Session summary with liked items and stats

## Project Structure

```
frontend/               # Next.js app
  src/
    app/
      mirror/           # Mirror display (kiosk)
      phone/            # Phone onboarding
      admin/            # Admin dashboard
    hooks/              # Camera, STT, gestures, pose detection, avatar
    components/mirror/  # ClothingCanvas, ProductCarousel, SpeechDisplay, etc.
    lib/                # API client, TTS, emotion parser, socket

backend/                # FastAPI server
  agent/                # Mira orchestrator, prompts, tools
  routers/              # REST endpoints (auth, queue, TTS, admin)
  mcp_server/           # MCP server for external AI integrations
  scraper/              # Gmail scraping
  services/             # Serper, Gemini, background removal
  models/               # Pydantic models, DB schemas
  migrations/           # Raw SQL migrations
```

## Testing

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## License

Private repository.
