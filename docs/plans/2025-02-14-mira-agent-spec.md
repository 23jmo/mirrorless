# Mira Agent — Technical Specification

## Overview

Mira is the AI personal stylist powering the Mirrorless smart mirror. She's a proactive, confident, direct-but-loving personality that roasts your outfit, flexes knowledge of your purchase history, and recommends clothing items one at a time in a swipe-style flow. Sessions last 2-3 minutes.

## Personality

- **Tone**: Direct but loving. Calls things out by name with warmth. "Oh honey, those cargo shorts are doing a LOT of heavy lifting right now."
- **Data usage**: Very aggressive. The wow factor IS that Mira knows your purchase history. She leads with it, references it constantly. "9 orders from ASOS? We need to talk."
- **Confidence**: Never breaks character. If search results are bad, she makes it work — never admits the data is off.
- **Proactive**: Never lets silence linger. If the user is quiet for 3-5 seconds, Mira fills the gap with a comment, question, or observation.
- **Session arc**: Always ends with a genuine confidence boost and recap of favorites, directing user to check their phone for links.

## Input Processing

### Event Model: Immediate on Voice

- **Primary trigger**: Voice input. When Deepgram detects end-of-speech, fire immediately.
- **Concurrent signals**: Any gestures (swipe, thumbs up/down) or pose changes happening at the same time are attached as context to the voice event.
- **Gesture-only events**: Swipe left/right and thumbs up/down fire independently when no voice is active.
- **Pose changes**: Detected via MediaPipe BlazePose, sent as events when significant change occurs.
- **Silence detection**: If no input for 3-5 seconds, synthesize a "silence" event so Mira can initiate.

### Input Types

| Input | Source | Event Format |
|-------|--------|-------------|
| Voice | Deepgram STT | `{type: "voice", transcript: "...", timestamp: ...}` |
| Swipe right | MediaPipe Hands | `{type: "gesture", gesture: "swipe_right"}` |
| Swipe left | MediaPipe Hands | `{type: "gesture", gesture: "swipe_left"}` |
| Thumbs up | MediaPipe Hands | `{type: "gesture", gesture: "thumbs_up"}` |
| Thumbs down | MediaPipe Hands | `{type: "gesture", gesture: "thumbs_down"}` |
| Pose change | MediaPipe BlazePose | `{type: "pose", snapshot_url: "...", landmarks: [...]}` |
| Silence | Timer | `{type: "silence", duration_seconds: 5}` |
| Camera snapshot | Webcam | `{type: "snapshot", image_base64: "..."}` |

## Tools

### 1. `search_clothing`

Calls Serper.dev Shopping API. Returns structured product JSON.

**Input**: `{query: string, num_results?: number}`

**Output**: Array of `{title, source, price, price_numeric, image_url, link, product_id, rating, rating_count}`

**Behavior**:
- Mira crafts the search query based on conversation context + user profile
- Results are broadcast in parallel: Claude receives them for narration AND frontend receives them for immediate UI rendering
- Mira presents items one at a time, reacting to user swipes

### 2. `search_gmail`

Searches the user's Gmail for specific information during conversation.

**Input**: `{query: string}`

**Output**: Array of email snippets matching the query

**Use case**: Contextual deep-dives. User mentions a specific purchase, Mira searches for the receipt. NOT for initial profile building (that's done pre-session during queue wait).

### 3. `get_user_profile`

Retrieves the user's pre-built style profile.

**Input**: `{user_id: string}`

**Output**: `{brands: string[], price_range: {min, max, avg}, style_tags: string[], purchases: Purchase[], narrative_summary: string}`

**Note**: This data is also injected into Mira's system prompt for instant access. The tool exists as a fallback if context window gets long and system prompt data is compressed.

## Architecture

### Orchestrator: Custom Event-Driven Loop

```
[Input Sources]                    [Orchestrator]                    [Output]
                                        │
Deepgram STT ──────┐                   │
MediaPipe Hands ───┤                   │
MediaPipe Pose ────┤──▶ Event Queue ──▶│──▶ Claude API (Haiku 4.5) ──▶ HeyGen TTS
Silence Timer ─────┤                   │         │                        │
Camera ────────────┘                   │    Tool Calls ──▶ Serper API    │
                                        │         │                        │
                                        │    Parallel ──▶ Frontend        │
                                        │    Broadcast    (product cards)  │
                                        │                                  │
                                  Socket.io ◀──────────────────────────────┘
                                        │
                                  Frontend Mirror Display
```

### Event Processing Flow

1. Input event arrives (voice end, gesture, pose change, silence timeout)
2. Orchestrator collects any concurrent events within a brief window (~200ms)
3. Builds Claude API message with:
   - System prompt (Mira personality + user profile data + session state)
   - Conversation history
   - Current event(s) as user message
   - Available tools
4. Streams Claude response to HeyGen token-by-token for immediate speech
5. If Claude calls a tool:
   - Execute tool call
   - Broadcast result to both Claude (continue generation) AND frontend (render UI)
   - Mira speaks filler while tool executes ("Let me pull something up...")
6. Update conversation history

### System Prompt Structure

```
[Mira Personality Instructions]
- Direct but loving roast style
- Always proactive, fill silence
- Never break character
- Reference purchase data aggressively

[User Profile]
- Name, style tags, brand affinities
- Price range: {min}-{max}, avg {avg}
- Recent purchases: [list]
- Style narrative: "..."

[Previous Session Memory]
- Past session summaries (liked items, reactions, conversation highlights)

[Session State]
- Current item index
- Items shown so far
- User reactions (likes/dislikes)
- Time elapsed

[Session Goals]
- Guided freeform: introduce, analyze outfit, recommend items, wrap up
- Soft limit: ~20 API calls, then start wrapping up naturally
- End with confidence boost + recap of favorites + "check your phone"
```

## Session Flow

### Guided Freeform (no rigid phases, goals-based)

**Goals Mira works toward:**

1. **Introduce** — Bold opener flexing knowledge of their data. Hit them with a surprising purchase insight.
2. **Analyze current outfit** — Camera snapshot → Claude Vision. Compare what they're wearing to their purchase history. "You own a lot of minimalist pieces but today you went bold — interesting."
3. **Recommend** — Search and present items one at a time. Mira leads the search direction based on profile + conversation. User redirects anytime.
4. **React to feedback** — On dislike: Mira makes an educated guess about why ("Not feeling the color? Or is it a price thing?"), user confirms/denies, Mira adapts.
5. **Close** — Genuine confidence boost, verbal recap of favorites, direct to phone for links.

**Mira controls the pacing** but follows the user's energy. If they're chatty, she matches. If they're quiet, she drives.

## Recommendation Logic

### Search Strategy

- Mira analyzes user profile (brands, style tags, price range) to craft search queries
- Price-aware: stays within ~1.5x of user's average purchase price
- Conversation-driven: Mira proposes directions, user reacts, Mira refines

### Item Presentation

- One item at a time, swipe-style
- On **thumbs up / swipe right**: Save to favorites, continue to next
- On **thumbs down / swipe left**: Mira makes educated guess about the issue, adapts future picks
- On **voice feedback**: Mira responds naturally, adjusts approach

### Tool Result Data Flow (Parallel Broadcast)

When `search_clothing` returns:
1. **Frontend** receives product list via Socket.io → renders first item card immediately
2. **Claude** receives results → generates Mira's commentary
3. User sees the product card while Mira starts talking about it

## Response Streaming

- Claude API responses streamed token-by-token to HeyGen LiveAvatar
- Mira starts speaking as soon as first tokens arrive — minimal perceived latency
- Tool call filler: Mira generates a transition line before tool execution ("Let me find something for you...")

## Session Memory (Persistent)

- After each session, store a summary: items shown, reactions, conversation highlights, style insights
- On return visits, Mira references past sessions: "Last time you loved that denim jacket — still haven't bought it huh?"
- Stored in `sessions` + `session_outfits` tables, with a `session_summary` text field for Claude context

## Error Handling

- **Mira stays in character**. All errors are handled gracefully in her voice.
- Serper API fails: "Hmm, my shopping powers are glitching. Let's keep talking while I figure this out."
- HeyGen fails: Fall back to text display on mirror
- Deepgram fails: Fall back to gesture-only mode, Mira drives conversation proactively
- Full error details logged to console for debugging

## API Budget

- **Soft limit**: ~20 Claude API calls per session
- After hitting the soft limit, Mira naturally steers toward wrapping up
- No hard cutoff — she finishes her current thought and closes gracefully

## Tech Stack

- **LLM**: Claude Haiku 4.5 via Anthropic API (streaming)
- **STT**: Deepgram streaming
- **TTS/Avatar**: HeyGen LiveAvatar API
- **Shopping data**: Serper.dev Shopping API
- **Body tracking**: MediaPipe BlazePose + Hands (browser)
- **Real-time**: Socket.io
- **Backend**: Python FastAPI
- **Database**: Neon Postgres (user profiles, sessions, memory)

## Files

```
backend/
  agent/
    orchestrator.py    # Event loop, Claude API calls, tool dispatch
    prompts.py         # Mira personality prompt, system prompt builder
    tools.py           # Tool definitions (search_clothing, search_gmail, get_user_profile)
    memory.py          # Session memory: save summaries, load past sessions
  services/
    serper_search.py   # Serper.dev Shopping API client (already built)
    deepgram_stt.py    # Deepgram streaming STT integration
    heygen_avatar.py   # HeyGen LiveAvatar TTS integration
```
