# Poke Smart Mirror — Full Flow

## The Setup

Three things are running:

| Service | What it does | URL |
|---------|-------------|-----|
| **Backend** | Socket.io server + mirror bridge REST API | `localhost:8002` |
| **MCP Server** | Exposes 5 tools to Poke via MCP protocol | `localhost:8001` (tunneled to public URL) |
| **Frontend** | Mirror display (`/mirror`) + debug chat (`/chat`) | `localhost:3002` |

Poke (the AI agent running on interaction.co) connects to the MCP server's public tunnel URL. That's its only link to our system.

---

## Step 1: Mirror Boots Up

The physical mirror (a TV running Chrome in full-screen) loads `/mirror?mirror_id=MIRROR-A1`.

On load, it:
- Opens a webcam feed (the "mirror" reflection)
- Connects to the backend via Socket.io
- Joins the room `mirror:MIRROR-A1`
- Waits for events

The mirror is now a dumb display surface. It shows whatever Poke pushes to it.

---

## Step 2: User Connects to Their Mirror via Poke

The user already has Poke (via iMessage, Telegram, or SMS). Their first message tells Poke which mirror to use:

> **User**: connect to my smart mirror: MIRROR-A1

Poke remembers `mirror_id = MIRROR-A1` for this user. From now on, every tool call targets that mirror.

*(How the user learns their mirror_id: it's shown as a badge in the top-left corner of the mirror display. Could also be a QR code that opens a deep link — future enhancement.)*

---

## Step 3: Poke Starts a Shopping Session

Following the MCP instructions, Poke:

1. **Calls `get_past_sessions("MIRROR-A1")`** — checks if this mirror has history
2. **Calls `send_to_mirror("MIRROR-A1", "Hey! Let's find you something great today.")`** — greeting appears on the mirror + spoken via TTS
3. Asks the user what they're looking for

> **User**: I need a denim jacket, something classic

---

## Step 4: Search → Curate → Display

4. **Poke calls `search_clothing("mens classic denim jacket medium wash")`**
   - MCP server → Serper Shopping API → returns 8 product results
   - Results go to Poke only (user doesn't see them yet)

5. **Poke picks its top 3-5 results, calls `present_items("MIRROR-A1", [...])`**
   - MCP server → `POST /api/mirror/present` → Socket.io emits `tool_result` to `mirror:MIRROR-A1`
   - Mirror displays product cards (image, title, price, source)
   - Chat page shows the same cards

6. **Poke calls `send_to_mirror("MIRROR-A1", "I picked these based on your style...")`**
   - Text overlay appears on mirror + spoken aloud
   - Chat page shows it as a "Mira" message

---

## Step 5: Conversation Continues

The user can respond in two ways:

**Via Poke (iMessage/Telegram/SMS):**
> **User**: I like the Levi's one but can you find something cheaper?

Poke processes this naturally and calls `search_clothing` again with refined query.

**Via the `/chat` page** (debug/demo tool):
- User types in the chat input
- Frontend POSTs to `POST /api/mirror/chat` with `{ mirror_id, text }`
- Backend relays to Poke's inbound webhook (`POST poke.com/api/v1/inbound-sms/webhook`)
- Poke receives it as if the user texted it
- Poke processes → calls MCP tools → results flow back to mirror

---

## Step 6: Session Ends

When the conversation wraps up, Poke:

7. **Calls `save_session("MIRROR-A1", "Looked at denim jackets, liked the Levi's Trucker", ...)`**
   - Saves to database so next session can reference it

---

## Data Flow Diagram

```
┌──────────────┐     text      ┌──────────┐    MCP tools     ┌────────────┐
│  User Phone  │ ────────────→ │   Poke   │ ───────────────→ │ MCP Server │
│ (iMessage/   │ ←──────────── │  (AI)    │ ←─────────────── │ :8001      │
│  Telegram)   │   responses   │          │   tool results   │            │
└──────────────┘               └──────────┘                  └─────┬──────┘
                                                                   │ HTTP
                                                                   ▼
┌──────────────┐   Socket.io   ┌────────────────────────────────────┐
│    Mirror    │ ←──────────── │          Backend :8002              │
│   Display    │               │  /api/mirror/present → tool_result │
│   /mirror    │               │  /api/mirror/text   → mirror_text  │
└──────────────┘               └────────────────────────────────────┘

┌──────────────┐   Socket.io        ▲
│  Chat Page   │ ←──────────────────┘
│   /chat      │ ──→ POST /api/mirror/chat ──→ Poke webhook
└──────────────┘     (relay user text to Poke)
```

---

## What the Mirror Shows

At any given moment, the mirror displays:
- **Webcam feed** — user sees their reflection
- **Product cards** — horizontal carousel at the bottom (from `present_items`)
- **Text overlay** — centered text bubble at the top (from `send_to_mirror`)
- **Mirror ID badge** — small label top-left (e.g., `MIRROR-A1`)

Gesture detection (thumbs up/down, swipe) animates the carousel locally but doesn't send events to Poke (yet).

---

## What's Missing / Future

- **QR code on mirror** → scans to a deep link that texts Poke "connect to MIRROR-A1" automatically
- **Gesture → Poke** → swipe/thumbs could relay to Poke as feedback
- **Voice input on mirror** → Deepgram STT → relay transcript to Poke (like the chat relay)
- **Merge with Mira** → main worktree has the Mira orchestrator; eventually one backend supports both
