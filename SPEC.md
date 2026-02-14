# Mirrorless — Full Project Specification

Mirrorless is a hackathon project (36h, 4+ people in pairs) — an AI-powered smart mirror that provides hyper-personalized clothing recommendations. Users onboard via phone, get their purchase history and style analyzed, then step up to a physical mirror where AI stylist "Mira" gives them outfit recommendations overlaid on their body in real-time. An MCP server exposes user taste data to Poke and other services.

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│  Phone UI   │────▶│  Next.js on  │────▶│  Python FastAPI │
│ (onboarding │◀────│   Vercel     │◀────│   on Render     │
│  + dashboard)│     │  (frontend)  │     │   (backend)     │
└─────────────┘     └──────┬───────┘     └───────┬────────┘
                           │                      │
                    Socket.io              ┌──────┴──────┐
                           │               │             │
                    ┌──────▼───────┐  Neon Postgres  Claude API
                    │ Mirror Display│     (DB)      (Haiku 4.5)
                    │ (full-screen  │                    │
                    │  Chrome on TV)│              ┌─────┴──────┐
                    └──────────────┘              │  SerpAPI    │
                         │                        │  Deepgram   │
                    MediaPipe                     │  HeyGen     │
                    (pose + hands)                └────────────┘
```

## Tech Stack

- **Frontend**: Next.js (mirror display + phone UI + onboarding)
- **Backend**: Python FastAPI
- **Database**: Neon Postgres
- **Real-time**: Socket.io
- **STT**: Deepgram streaming
- **TTS/Avatar**: HeyGen LiveAvatar API
- **Body tracking**: MediaPipe (BlazePose + Hand landmarks)
- **Clothing sourcing**: SerpAPI / Google Shopping API
- **AI**: Claude API (Haiku 4.5 via Anthropic API with OAuth + beta headers)
- **Auth**: Google OAuth (Gmail + Calendar scopes)
- **Deploy**: Vercel (frontend) + Render (Python backend)

## Core Components

### 1. Onboarding (Phone → Mobile Web)

- QR code → Next.js mobile page
- Google OAuth (scopes: Gmail read, Calendar read, profile)
- Collect name, phone number
- Link to Poke signup: https://poke.com/treehacks
- After onboarding, phone becomes session dashboard

### 2. Data Scraping Pipeline

**Fast pass (~10-15s, all in parallel)**:
- Recent 5-10 receipt emails from major retailers
- Brand frequency scan from last 100 email subject lines
- Google profile photo for initial style assessment

**Background deep scrape (async)**:
- Full inbox: all receipts, newsletter subscriptions, shipping notifications
- Calendar events for lifestyle context (gym, travel, meetings)
- Results stream to agent context as they complete

**MVP cut**: Skip Google Photos analysis

### 3. AI Agent — Mira

**Architecture**: Custom event-driven orchestrator (NOT Agents SDK)
- Central event loop receives: voice transcripts, gesture events, pose data, scraping updates
- Batches events and calls Claude API when meaningful input arrives
- Maintains conversation history and user context

**Voice**: Deepgram streaming STT → Claude → HeyGen LiveAvatar TTS

**Vision**: Event-triggered snapshots (gesture detected, pose change, user speaks) sent to Claude Vision

**Tools available to agent**:
- `search_clothing` — Search for clothing items via SerpAPI
- `get_user_profile` — Retrieve user's style profile and preferences
- `get_purchase_history` — Fetch user's purchase history from scraped data
- `analyze_current_outfit` — Analyze user's current outfit from camera snapshot

**Personality**: Friendly, teasy/jokey, references purchase data ("I see you've been on an Aritzia spree...")

**Error handling**: Mira acknowledges issues in character + full error logs to console

### 4. Mirror Display (Full-screen Chrome Web App)

- Next.js app rendered in full-screen Chrome on external monitor/TV behind two-way mirror
- Webcam feed via `getUserMedia`
- MediaPipe BlazePose for body landmark detection
- 2D clothing overlay: affine transforms to warp clothing images onto body keypoints
- Mira avatar: liquid glass aesthetic, animated, floats around the screen
- Fallback: static side-by-side display if overlay doesn't work

### 5. Clothing Recommendations

- **Source**: SerpAPI / Google Shopping API
- **Engine**: Claude (Haiku 4.5) as recommendation brain
- **Flow**: User profile + search results → Claude selects outfit combinations → explains choices with personality

### 6. Gesture Control (MediaPipe Hands)

- **Swipe right** → next outfit recommendation
- **Swipe left** → previous outfit
- **Thumbs up** → save/like outfit
- **Thumbs down** → skip/dislike

### 7. Phone Dashboard

- **In queue**: Position number + live mirror preview stream
- **During session**: Live view (optional)
- **After session**: Full recap — outfits viewed, favorites, prices, buy links, style insights

### 8. Queue System

- Users onboard → enter queue → background scraping runs during wait
- Phone shows queue position + live mirror preview
- Session starts when previous user finishes

### 9. MCP Server (for Poke Integration)

- **Format**: Structured JSON + natural language style summary
- **Endpoints**:
  - Read user shopping tastes (brands, price range, style preferences)
  - View previous mirror sessions (outfits viewed, reactions)
  - Webhook: fires on session end with full summary (user ID, outfits, favorites, buy links)
  - Poke texts user with session recap + outfit links

### 10. Deployment

- Next.js → Vercel
- Python FastAPI → Render
- Neon Postgres (via MCP tools)
- Mirror laptop connects to deployed backend URLs

## Team Structure (2 Pairs)

- **Pair 1 — Mirror Experience**: Overlay rendering, gesture detection, mirror UI, Mira avatar, HeyGen integration
- **Pair 2 — Data Pipeline**: Gmail scraping, agent orchestrator, Claude integration, SerpAPI, MCP server, phone UI

## Database Schema (Neon Postgres)

### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK, default gen_random_uuid() |
| name | text | |
| email | text | unique |
| phone | text | |
| google_oauth_token | jsonb | access + refresh tokens |
| poke_id | text | nullable |
| created_at | timestamptz | default now() |

### `style_profiles`
| Column | Type | Notes |
|--------|------|-------|
| user_id | uuid | FK → users.id |
| brands | text[] | detected brand preferences |
| price_range | jsonb | {min, max, avg} |
| style_tags | text[] | e.g. ["streetwear", "minimalist"] |
| size_info | jsonb | nullable |
| narrative_summary | text | AI-generated style narrative |

### `purchases`
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| user_id | uuid | FK → users.id |
| brand | text | |
| item_name | text | |
| category | text | e.g. "tops", "shoes" |
| price | numeric | |
| date | date | |
| source_email_id | text | Gmail message ID |

### `sessions`
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| user_id | uuid | FK → users.id |
| started_at | timestamptz | |
| ended_at | timestamptz | nullable |
| status | text | "active", "completed", "abandoned" |

### `session_outfits`
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| session_id | uuid | FK → sessions.id |
| outfit_data | jsonb | full outfit details |
| reaction | text | "liked", "disliked", "skipped" |
| clothing_items | uuid[] | FK refs to clothing_items |

### `clothing_items`
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| name | text | |
| brand | text | |
| price | numeric | |
| image_url | text | |
| buy_url | text | |
| category | text | |
| source | text | "serpapi", "manual" |

### `queue`
| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| user_id | uuid | FK → users.id |
| position | integer | |
| status | text | "waiting", "active", "completed" |
| joined_at | timestamptz | default now() |
