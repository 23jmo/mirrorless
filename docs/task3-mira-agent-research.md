# Mira AI Agent — Research Report

> **Feature 3 from SPEC.md**: Custom event-driven AI agent orchestrator for the Mirrorless smart mirror.
>
> This document synthesizes findings from 5 parallel research agents investigating the best way to build the Mira AI Agent.

**Date**: 2026-02-14

---

## Table of Contents

1. [Agent 1: Event-Driven Architecture](#1-event-driven-architecture)
2. [Agent 2: Claude API Integration (Tool Use, Vision, Streaming)](#2-claude-api-integration)
3. [Agent 3: Voice Pipeline (Deepgram STT + HeyGen TTS)](#3-voice-pipeline)
4. [Agent 4: Socket.io Real-Time Communication](#4-socketio-real-time-communication)
5. [Agent 5: Codebase Analysis](#5-codebase-analysis)

---

## 1. Event-Driven Architecture

### 1.1 Event Batching Strategy

The industry standard for real-time interactive systems uses **hybrid batching with time-windowing and priority tiers**. For streaming conversational AI, batching intervals typically range from 200ms to 500ms.

**Recommended: Priority-based time-windowed batching (300ms)**

- **Time window**: 300ms (balanced between responsiveness and throughput)
  - Faster than typical turn-based agents (1-2s)
  - Slower than ultra-low-latency financial systems (10-50ms)
  - Matches human conversational perception (~200-300ms is imperceptible)

- **Priority tiers** (process in this order):
  1. **High**: Voice transcripts (user input has highest priority)
  2. **Medium**: Gesture events (modifies user intent)
  3. **Low**: Pose data (ambient awareness, lower urgency)
  4. **Background**: Scraping updates (async, batched separately)

```python
class EventBatcher:
    def __init__(self, window_ms=300):
        self.high_priority_queue = asyncio.Queue()
        self.medium_priority_queue = asyncio.Queue()
        self.low_priority_queue = asyncio.Queue()
        self.window_ms = window_ms

    async def batch_events(self):
        """Collect events for window_ms, emit prioritized batch"""
        batch = {
            'voice_transcripts': [],
            'gestures': [],
            'pose': [],
            'timestamp': time.time()
        }

        deadline = time.time() + (self.window_ms / 1000)

        while time.time() < deadline:
            for queue, key in [
                (self.high_priority_queue, 'voice_transcripts'),
                (self.medium_priority_queue, 'gestures'),
                (self.low_priority_queue, 'pose')
            ]:
                try:
                    while True:
                        batch[key].append(queue.get_nowait())
                except asyncio.QueueEmpty:
                    pass

            await asyncio.sleep(0.01)

        return batch
```

**Key insight**: vLLM's continuous batching blends request queuing with micro-batching — apply this principle: accept events continuously but only invoke Claude every 300ms.

### 1.2 Event Loop Design

**Recommended: asyncio + pub/sub with in-memory queues**

For a hackathon project on a single Render instance, asyncio + pub/sub outperforms heavy message brokers (Redis/Kafka). Reserve those for multi-instance scaling.

```python
class EventOrchestrator:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {
            'voice_transcript': [],
            'gesture_detected': [],
            'pose_frame': [],
            'scraping_complete': [],
        }
        self.event_queue = asyncio.Queue()
        self.batcher = EventBatcher(window_ms=300)

    def subscribe(self, event_type: str, callback: Callable):
        self.subscribers[event_type].append(callback)

    async def publish(self, event_type: str, data: dict):
        await self.event_queue.put({
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        })

    async def run_event_loop(self):
        while True:
            batch = await self.batcher.batch_events()
            response = await self.invoke_mira(batch)
            for callback in self.subscribers.get('mira_response', []):
                await callback(response)
```

**Rationale**:
- **asyncio**: Native Python, zero external dependencies, runs on single Render instance
- **Pub/sub**: Decouples event producers (voice, gesture, pose) from consumers (Claude calls, display updates)
- **Queue-based batching**: Simpler than state machines for this use case

### 1.3 Context Management

Claude Haiku 4.5 has a **200k token context window** with a **64k output token limit**.

**Token Budget**:
```
System prompt (Mira's personality):  ~2,000 tokens
Session state (user profile, style):  ~3,000 tokens
Recent conversation (last 10 turns):  ~8,000 tokens
Current batch (voice + events):       ~2,000 tokens
Reserve for response:                 ~5,000 tokens
TOTAL USED: ~20,000 tokens
Available capacity: ~180,000 tokens (90% of window)
```

**Recommended: Anchored Summaries (Factory.ai pattern)**

Keep the last ~10 exchanges verbatim (preserves tone/style nuance), compress everything older into a summary.

```python
class ContextManager:
    def __init__(self, max_context_tokens=20000):
        self.max_context_tokens = max_context_tokens
        self.summary = ""
        self.recent_history = []  # Verbatim last 10 exchanges

    async def add_exchange(self, user_msg: str, assistant_msg: str):
        self.recent_history.append({'user': user_msg, 'assistant': assistant_msg})
        if len(self.recent_history) > 10:
            await self._compress_old_exchanges()

    async def _compress_old_exchanges(self):
        to_compress = self.recent_history[:-10]
        # Use Claude to summarize old exchanges
        # Preserve: style preferences, outfit choices, personal context
        self.recent_history = self.recent_history[-10:]

    def get_context_for_claude(self) -> str:
        return f"SUMMARY:\n{self.summary}\n\nRECENT:\n{self._format_history()}"
```

### 1.4 Concurrency Model

**Debouncing + Priority Queues**:
- **Pose**: Debounce to 100ms (10 FPS). Humans perceive ~100ms pose changes; faster is waste
- **Gestures**: Debounce to 50ms (20 Hz). Discrete events; sample at 2x Nyquist
- **Voice**: No debouncing. Every transcript chunk is meaningful

```python
class ConcurrencyController:
    def __init__(self):
        self.pose_debounce_ms = 100
        self.gesture_debounce_ms = 50
        self.last_pose_update = 0
        self.last_gesture_update = 0

    async def accept_pose_frame(self, pose_data: dict):
        now = time.time() * 1000
        if now - self.last_pose_update < self.pose_debounce_ms:
            return  # Drop this frame
        self.last_pose_update = now
        await self.orchestrator.publish('pose_frame', pose_data)
```

### 1.5 State Machine Design

**Recommended: Hybrid (Minimal FSM + Claude-driven state)**

Define a lightweight state machine with 5 core states, but let Claude's responses manage transitions:

```python
class MiraState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    SHOWING_OUTFIT = "showing_outfit"
```

**State Diagram**:
```
IDLE
  | (voice transcript received)
LISTENING
  | (batch window closes)
THINKING
  | (Claude responds)
SPEAKING (if response required)
  | (HeyGen finishes)
SHOWING_OUTFIT (if outfit to display)
  | (user gestures or timeout)
IDLE
```

### 1.6 Implementation Stack Summary

| Component | Recommendation | Rationale |
|-----------|---------------|-----------|
| Event Loop | Python asyncio | Native, no deps, single Render instance |
| Batching | Time-windowed (300ms) + priority queues | Balances latency vs throughput |
| Pub/Sub | In-memory asyncio.Queue + subscribers | Simple, extensible to Redis later |
| Context | Anchored summaries | Preserves 180k token buffer |
| Rate Limiting | Debouncing per event type + queue limits | Prevents sensor overwhelm |
| State | Minimal 5-state FSM + Claude-driven logic | Flexibility of LLM, safety of FSM |

### Sources
- [Top AI Agent Orchestration Frameworks for Developers 2025](https://www.kubiya.ai/blog/ai-agent-orchestration-frameworks)
- [Four Design Patterns for Event-Driven, Multi-Agent Systems](https://www.confluent.io/blog/event-driven-multi-agent-systems/)
- [2025 Voice AI Guide](https://programmerraja.is-a.dev/post/2025/2025-Voice-AI-Guide-How-to-Make-Your-Own-Real-Time-Voice-Agent-(Part-1))
- [Mastering Event-Driven Architecture in Python with AsyncIO](https://medium.com/data-science-collective/mastering-event-driven-architecture-in-python-with-asyncio-and-pub-sub-patterns-2b26db3f11c9)
- [Context Windows - Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/context-windows)
- [Context Window Management Strategies](https://www.getmaxim.ai/articles/context-window-management-strategies-for-long-context-ai-agents-and-chatbots/)
- [LLM Chat History Summarization Guide](https://mem0.ai/blog/llm-chat-history-summarization-guide-2025)

---

## 2. Claude API Integration

### 2.1 Tool Use with Haiku 4.5

Claude Haiku 4.5 is fully capable for tool use. No beta headers needed.

**Mira's Tools**:

```python
tools = [
    {
        "name": "search_clothing",
        "description": "Search for clothing items matching style, category, and price.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Style or clothing type to search"},
                "category": {"type": "string", "enum": ["tops", "bottoms", "shoes", "outerwear", "accessories", "dresses"]},
                "price_range": {
                    "type": "object",
                    "properties": {
                        "min": {"type": "number"},
                        "max": {"type": "number"}
                    }
                }
            },
            "required": ["query", "category"]
        }
    },
    {
        "name": "get_user_profile",
        "description": "Retrieve user's style profile (brands, preferences, price range). Call once per session at start.",
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "string"}},
            "required": ["user_id"]
        }
    },
    {
        "name": "get_purchase_history",
        "description": "Fetch user's recent purchases for personality-driven commentary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "limit": {"type": "integer", "default": 20}
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "analyze_current_outfit",
        "description": "Analyze user's outfit from camera snapshot. Returns structured analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_base64": {"type": "string"},
                "focus": {"type": "string", "enum": ["full_body", "upper_body", "lower_body", "color_analysis"]}
            },
            "required": ["image_base64"]
        }
    }
]
```

**Tool Loop Pattern**:

```python
def handle_tool_use_loop(user_id: str, user_message: str, camera_image_base64: str = None):
    messages = [{"role": "user", "content": user_message}]

    # Add vision content if camera snapshot provided
    if camera_image_base64:
        messages[0]["content"] = [
            {"type": "text", "text": user_message},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": camera_image_base64}}
        ]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        tools=tools,
        system=MIRA_SYSTEM_PROMPT,
        messages=messages
    )

    # Loop while Claude wants to use tools
    while response.stop_reason == "tool_use":
        tool_uses = [block for block in response.content if block.type == "tool_use"]
        tool_results = []
        for tool_use in tool_uses:
            result = execute_tool(tool_use.name, tool_use.input, user_id)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": str(result)
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=tools,
            system=MIRA_SYSTEM_PROMPT,
            messages=messages
        )

    return "".join(block.text for block in response.content if block.type == "text")
```

### 2.2 Vision Integration

- **Supported formats**: JPEG, PNG, GIF, WebP
- **Maximum size**: 20MB
- **Recommended for real-time mirror**: 640x480 JPEG (quality 0.6-0.8)
- **Token cost**: 640x480 JPEG = ~65 tokens; 1280x720 = ~200 tokens

**Quality/Latency Tradeoffs**:
- **For gesture/pose events** (frequent): 480p snapshots → ~50-100ms encoding + ~500ms Claude latency
- **For outfit analysis** (less frequent): 720p → ~200-300ms encoding + ~600ms Claude latency
- **Recommendation**: 640x480 for real-time streams, 720p for user-initiated "analyze my outfit"

### 2.3 Streaming Responses

Streaming is recommended for real-time mirror UX:
- Partial text appears while Mira is "thinking"
- Perceived latency reduction (first words in ~300ms vs full response in ~1s)
- Tool use streaming available on Haiku 4.5 (no beta header required)

```python
def stream_agent_with_tools_loop(user_id: str, user_message: str):
    messages = [{"role": "user", "content": user_message}]

    while loop_count < 5:
        with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=tools,
            system=MIRA_SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            final_message = stream.get_final_message()

        if final_message.stop_reason != "tool_use":
            return "".join(b.text for b in final_message.content if b.type == "text")

        # Execute tools, append to messages, continue loop
```

**UX pattern**: Stream preamble ("Let me search for...") -> tool silently executes -> stream recommendation text

### 2.4 System Prompt Design

```python
MIRA_SYSTEM_PROMPT = """You are Mira, a witty and teasing AI stylist on a smart mirror.

## Personality
- Friendly, conversational, and playful
- Reference purchase history: "I see you've been on an Aritzia spree..."
- Confident but open to feedback

## Approach
1. Greet warmly, ask what they're looking for
2. Get context from profile (brands, style tags, price range)
3. Reference recent purchases
4. Analyze current outfit if shown
5. Search for items matching their aesthetic AND reality
6. Explain choices with personality

## Constraints
- Redirect non-fashion queries gracefully
- Keep recommendations realistic (match their price range)
- Max 150 words per response
- Reference colors, fit, occasions"""

# Inject user context at session start (reduces tool call tokens)
def build_system_prompt_with_context(user_profile: dict, purchase_history: list):
    context = f"""## Your User
- Favorite brands: {', '.join(user_profile.get('brands', [])[:5])}
- Style tags: {', '.join(user_profile.get('style_tags', []))}
- Average spend: ${user_profile.get('price_range', {}).get('avg', 'unknown')}"""
    return MIRA_SYSTEM_PROMPT + "\n\n" + context
```

### 2.5 Model Configuration

| Parameter | Value |
|-----------|-------|
| Model ID | `claude-haiku-4-5-20251001` |
| Alias | `claude-haiku-4-5` |
| API Version | `2023-06-01` (auto via SDK) |
| Beta Headers | None required |
| Max Tokens | 1024 (for chat responses) |

### 2.6 Cost & Latency Analysis

| Metric | Value |
|--------|-------|
| Input token cost | $1 / 1M tokens |
| Output token cost | $5 / 1M tokens |
| Typical latency | 300-800ms |
| Tool use latency | +200-400ms |
| Vision latency | +100-300ms |
| Cost per recommendation | ~$0.002-0.005 |
| 10 recommendations (session) | ~$0.02 |
| 100 hackathon sessions | ~$2 |

**Latency Breakdown**:
```
User speaks -> Deepgram STT (500ms) -> Backend processes
-> Stream Mira intro (200ms) -> Tool execution (400ms parallel)
-> Stream recommendation (300ms) -> HeyGen TTS (800ms)
= ~2-3s total end-to-end
```

### Sources
- [Introducing Claude Haiku 4.5](https://www.anthropic.com/news/claude-haiku-4-5)
- [Models Overview - Claude API Docs](https://platform.claude.com/docs/en/about-claude/models/overview)
- [How to Implement Tool Use - Claude API Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use)
- [Streaming Messages - Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/streaming)

---

## 3. Voice Pipeline

### 3.1 Deepgram Streaming STT

**Recommended Model**: Deepgram Nova-3

**Latency Performance**:
- First-word latency: ~150ms
- Streaming transcripts: under 300ms
- Interim results: within 150ms (for live captions)
- Production deployments: first-word under 300ms, conversational flow under 500ms total

**Endpointing Configuration**:
- Default: 10ms of silence triggers `speech_final: true`
- Recommended for mirror: `endpointing=500` (500ms silence = end of utterance)
- For longer pauses: `utterance_end_ms=1000` with `interim_results=true`
- VAD-based detection distinguishes background noise from speech

```python
# Backend Deepgram integration
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

async def init_deepgram_stream(api_key: str, on_transcript: callable):
    deepgram = DeepgramClient(api_key)
    connection = deepgram.listen.asynclive.v("1")

    options = LiveOptions(
        model="nova-3",
        language="en",
        smart_format=True,
        endpointing=500,        # 500ms silence = end of utterance
        interim_results=True,
        utterance_end_ms=1000,
    )

    async def on_message(self, result, **kwargs):
        transcript = result.channel.alternatives[0].transcript
        is_final = result.speech_final
        if transcript:
            await on_transcript(transcript, is_final)

    connection.on(LiveTranscriptionEvents.Transcript, on_message)
    await connection.start(options)
    return connection
```

**Key Architecture Decision**: Run Deepgram STT in the **browser** (frontend), not backend. Send only transcripts (text) over Socket.io — not raw audio. This eliminates audio streaming bandwidth and latency.

```typescript
// Frontend: Deepgram processes audio locally, emits transcript via Socket.io
connection.addListener("transcript", (data) => {
    const transcript = data.channel.alternatives[0].transcript;
    socket.emit("voice_transcript", {
        text: transcript,
        is_final: data.is_final,
        timestamp: performance.now(),
    });
});
```

### 3.2 HeyGen LiveAvatar TTS

**Integration Pattern**: WebRTC-based streaming avatar

**Key Methods**:

| Method | Purpose |
|--------|---------|
| `newSession()` | Creates and starts a new avatar session |
| `speak({ text, task_type: TaskType.REPEAT })` | Avatar speaks provided text |
| `startVoiceChat()` | Initiates voice chat |
| `interrupt()` | Halts current speaking task |
| `stopAvatar()` | Terminates the avatar session |

**Key Events**:
- `AVATAR_START_TALKING` / `AVATAR_STOP_TALKING`: Avatar speech lifecycle
- `STREAM_READY`: Stream is ready for display
- `USER_START` / `USER_STOP`: User interaction states
- `STREAM_DISCONNECTED`: Connection loss

```typescript
// Frontend: HeyGen avatar integration
import { StreamingAvatar, TaskType, StreamingEvents } from "@heygen/streaming-avatar";

const avatar = new StreamingAvatar({ token: HEYGEN_TOKEN });
await avatar.createStartAvatar({ avatarName: "mira", quality: "medium" });

avatar.on(StreamingEvents.AVATAR_START_TALKING, () => {
    // Show talking animation state
});

avatar.on(StreamingEvents.AVATAR_STOP_TALKING, () => {
    // Return to idle state
});

// When Mira has a response to speak:
async function miraSpeak(text: string) {
    await avatar.speak({ text, task_type: TaskType.REPEAT });
}
```

**Latency**: 2-4 seconds from text input to avatar speaking (WebRTC setup + synthesis)

### 3.3 Voice Interruption (Barge-In)

For barge-in detection:
- Use VAD (Voice Activity Detection) with 10-20ms audio chunk processing
- Detect when user speaks while avatar is talking
- Call `avatar.interrupt()` to stop HeyGen
- Cancel pending Claude responses

### 3.4 End-to-End Voice Latency

```
User speaks                      0ms
Deepgram STT (first word)     ~150ms
Deepgram STT (final)          ~500ms
Event batching (300ms window)  ~800ms
Claude API (Haiku streaming)  ~1,300ms
HeyGen avatar synthesis       ~3,300ms
Avatar starts speaking        ~3,500ms

Total: ~3.5-4 seconds
```

### 3.5 Fallback Strategy

If HeyGen is unavailable or too slow:
1. **Primary**: HeyGen LiveAvatar (visual avatar + voice)
2. **Fallback 1**: ElevenLabs Flash v2.5 (75ms latency, audio only)
3. **Fallback 2**: Browser Web Speech API (`speechSynthesis`) — zero latency, lower quality

### Sources
- [Deepgram Endpointing Docs](https://developers.deepgram.com/docs/endpointing)
- [Deepgram Streaming Latency](https://developers.deepgram.com/docs/measuring-streaming-latency)
- [Introducing Nova-3](https://deepgram.com/learn/introducing-nova-3-speech-to-text-api)
- [HeyGen Streaming Avatar SDK](https://docs.heygen.com/docs/streaming-avatar-sdk-reference)
- [Real-Time Barge-In AI](https://www.gnani.ai/resources/blogs/real-time-barge-in-ai-for-voice-conversations-31347)
- [ElevenLabs Latency Optimization](https://elevenlabs.io/docs/developers/best-practices/latency-optimization)

---

## 4. Socket.io Real-Time Communication

### 4.1 Event Flow Design

#### Mirror Display -> Backend Events

**`gesture_detected`** (800ms cooldown)
```typescript
{
  type: "swipe_left" | "swipe_right" | "thumbs_up" | "thumbs_down",
  confidence: number,    // 0.0-1.0
  timestamp: number,
  session_id?: string,
}
```

**`pose_landmarks`** (debounced ~100ms)
```typescript
{
  landmarks: [{ x, y, z, visibility }],  // 33 total (BlazePose)
  timestamp: number,
  visibility_score: number,
  frame_id: number,
}
```

**`camera_snapshot`** (event-triggered)
```typescript
{
  image_base64: string,   // JPEG compressed, max 50KB
  timestamp: number,
  mime_type: "image/jpeg",
  quality: number,        // 0-1, suggest 0.6
  trigger: "gesture" | "pose_change" | "voice_detected",
}
```

**`voice_transcript`** (from Deepgram STT)
```typescript
{
  text: string,
  is_final: boolean,
  timestamp: number,
  confidence: number,
}
```

#### Backend -> Mirror Display Events

**`agent_response`**
```json
{
  "message_id": "uuid",
  "text": "I see you've been shopping at Aritzia...",
  "session_id": "uuid",
  "avatar_state": {
    "animation": "talking" | "thinking" | "idle",
    "expression": "happy" | "neutral" | "surprised"
  },
  "audio_url": "https://heygen-avatar-output/...",
  "audio_duration_ms": 3200
}
```

**`outfit_recommendation`**
```json
{
  "recommendation_id": "uuid",
  "outfit_items": [
    {
      "id": "uuid",
      "name": "Oversized Blazer",
      "brand": "Aritzia",
      "image_url": "https://...",
      "category": "tops",
      "price": 189.99,
      "overlay_transform": {
        "type": "affine",
        "scale": 1.2,
        "translate_x": 50, "translate_y": 100,
        "rotation_degrees": -5,
        "keypoints": [
          { "landmark_index": 11, "x_offset": -20, "y_offset": 10 },
          { "landmark_index": 12, "x_offset": 20, "y_offset": 10 }
        ]
      }
    }
  ],
  "explanation": "Matches your minimalist aesthetic",
  "buy_url": "https://..."
}
```

#### Backend -> Phone Dashboard Events

**`scrape_progress`**, **`scrape_complete`**, **`queue_update`**, **`session_start_notification`**, **`outfit_history`**

#### Phone -> Backend Events

**`session_control`**: `{ action: "skip_outfit" | "like_outfit" | "end_session" }`

### 4.2 Session Management

**Room Structure**:
- `user_id` -> Phone + Mirror + all associated clients
- `mirror_{user_id}` -> Only mirror display
- `phone_{user_id}` -> Only phone dashboard

**Session Flow**:
1. Phone onboards -> POST `/auth/google` -> user_id created
2. Phone joins queue -> POST `/queue/join`
3. Phone connects Socket.io -> emits `join_room(user_id)`
4. Queue promotes user -> emits `session_start_notification`
5. Mirror connects -> emits `join_mirror_session(user_id, session_token)`
6. Backend creates `sessions` DB entry, status='active'

### 4.3 Binary Data Handling

**Recommendation: Base64 over Socket.io (not WebRTC)**

Reasons:
- Adds complexity (STUN/TURN servers, codec negotiation)
- Only need periodic snapshots, not continuous stream
- Hackathon timeline = simplicity first

**Compression**:

| Resolution | Quality | Size | Latency (50Mbps) |
|-----------|---------|------|-----------------|
| 1280x720 | 0.3 | 15-25 KB | 3-5ms |
| 1280x720 | 0.6 | 35-50 KB | 7-10ms |
| 640x360 | 0.6 | 12-18 KB | 2-4ms |

**Recommendation**: 640x360 @ quality 0.6 = ~15 KB per snapshot

### 4.4 Rate Limiting & Debouncing

| Event | Max Rate | Rationale |
|-------|----------|-----------|
| Gesture | 1/800ms | Cooldown enforced by classifier |
| Pose | 1/200ms | Throttle + similarity check |
| Snapshots | 1/2000ms | Debounce voice triggers |
| Voice transcript | ~5/sec | Deepgram's internal rate |
| Batch flush | 1/100ms | Client buffers raw events |

### 4.5 Reconnection & Resilience

**Frontend config**:
```typescript
const socket = io(SOCKET_URL, {
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  reconnectionAttempts: 10,
  transports: ["websocket", "polling"],
});

socket.on("connect", () => {
  // Re-join room with user_id
  socket.emit("join_room", { user_id });
});
```

**Backend**: Sessions marked as "paused" on disconnect, resumable within 30 minutes. Context preserved in `SessionStore` (in-memory, or Redis for production).

### 4.6 Event Architecture Diagram

```
PHONE (Browser)
  |-- emit "join_room"
  |-- emit "session_control"
  |-- listen "scrape_progress"
  |-- listen "scrape_complete"
  |-- listen "queue_update"
  |-- listen "session_start_notification"
  |-- listen "outfit_history"

MIRROR (Browser)
  |-- emit "join_mirror_session"
  |-- emit "gesture_detected"
  |-- emit "camera_snapshot"
  |-- emit "pose_landmarks"
  |-- emit "voice_transcript"
  |-- listen "agent_response"
  |-- listen "outfit_recommendation"
  |-- listen "outfit_changed"
  |-- listen "session_status"

BACKEND (FastAPI + python-socketio)
  |-- Room-based routing (user_id rooms)
  |-- SessionStore (context preservation)
  |-- Orchestrator (Claude API)
  |-- Database (Neon Postgres)
```

### Sources
- Socket.io rooms documentation
- python-socketio 5.11.4 documentation
- Existing codebase analysis (`backend/main.py`, `frontend/src/lib/socket.ts`)

---

## 5. Codebase Analysis

### 5.1 What Exists (47% complete)

| Component | Status | File | Lines |
|-----------|--------|------|-------|
| FastAPI app | WORKING | `backend/main.py` | 55 |
| Pydantic models | WORKING | `backend/models/schemas.py` | 106 |
| Neon DB client | WORKING | `backend/models/database.py` | 89 |
| Scraping pipeline | WORKING | `backend/scraper/pipeline.py` | 145 |
| Purchase parser | WORKING | `backend/scraper/purchase_parser.py` | 149 |
| Brand scanner | WORKING | `backend/scraper/brand_scanner.py` | 20 |
| Profile builder | WORKING | `backend/scraper/profile_builder.py` | 87 |
| Google OAuth | WORKING | `backend/services/auth.py` | 83 |
| Auth routes | WORKING | `backend/routers/auth.py` | 55 |
| Users routes | WORKING | `backend/routers/users.py` | 24 |
| Serper search | WORKING | `backend/services/serper_search.py` | 87 |
| Mirror page | WORKING | `frontend/src/app/mirror/page.tsx` | 110 |
| Gesture recognizer | WORKING | `frontend/src/hooks/useGestureRecognizer.ts` | 139 |
| Gesture classifier | WORKING | `frontend/src/lib/gesture-classifier.ts` | 68 |
| Camera hook | WORKING | `frontend/src/hooks/useCamera.ts` | 56 |
| Socket.io client | READY | `frontend/src/lib/socket.ts` | 8 |
| Phone UI | WORKING | `frontend/src/app/phone/page.tsx` | 84 |

### 5.2 What's Scaffolded (5%)

| Component | Status | File |
|-----------|--------|------|
| Agent orchestrator | EMPTY (1 line) | `backend/agent/orchestrator.py` |
| Agent prompts | EMPTY (1 line) | `backend/agent/prompts.py` |
| MCP server | EMPTY | `backend/mcp/` |

### 5.3 What's Missing (48%)

| Component | Estimated Lines | Priority |
|-----------|----------------|----------|
| `backend/agent/orchestrator.py` | 300-400 | CRITICAL |
| `backend/agent/prompts.py` | 100-200 | CRITICAL |
| `backend/services/deepgram.py` | 150 | HIGH |
| `backend/services/heygen.py` | 150 | HIGH |
| `backend/routers/sessions.py` | 150 | HIGH |
| `frontend/src/components/mirror/MiraAvatar.tsx` | 100-150 | HIGH |
| `frontend/src/components/mirror/OutfitDisplay.tsx` | 250-350 | HIGH |
| `frontend/src/lib/pose-overlay.ts` | 200 | MEDIUM |
| `frontend/src/hooks/useVoiceCapture.ts` | 100-150 | MEDIUM |
| `frontend/src/components/phone/SessionRecap.tsx` | 150-200 | LOW |
| `backend/mcp/server.py` | 200-300 | LOW |

### 5.4 Dependencies

All required dependencies are already installed:
- `anthropic==0.42.0`
- `deepgram-sdk==3.8.0`
- `python-socketio==5.11.4`
- `@mediapipe/tasks-vision` (frontend)
- `socket.io-client` (frontend)

### 5.5 Database Schema

All 7 tables exist and match SPEC.md:
- `users`, `style_profiles`, `purchases`, `sessions`, `clothing_items`, `session_outfits`, `queue`

### 5.6 Recommended Build Order

1. **Backend Agent Core** (critical path):
   - `backend/agent/orchestrator.py` + `backend/agent/prompts.py`
   - Test Claude API integration

2. **Backend Support Services**:
   - `backend/services/deepgram.py` + `backend/services/heygen.py`
   - `backend/routers/sessions.py`

3. **Frontend Outfit Display**:
   - `frontend/src/components/mirror/OutfitDisplay.tsx`
   - `frontend/src/lib/pose-overlay.ts`

4. **Frontend Avatar**:
   - `frontend/src/components/mirror/MiraAvatar.tsx`

5. **Frontend Voice**:
   - `frontend/src/hooks/useVoiceCapture.ts`

6. **Frontend Event Handlers**:
   - Extend `frontend/src/lib/socket.ts`

7. **Phone Recap + MCP Server** (last)

**Estimated total time**: 15-20 hours for experienced team

### 5.7 Integration Points

```
Frontend (Mirror)                    Backend
----------------------------------------------
[Mirror Page]  --gesture_detected--> [Orchestrator]
[Camera/MediaPipe]                    | (batch events)
                                      | (call Claude API)
[OutfitDisplay] <-outfit_recommendation-|
[MiraAvatar]    <-agent_speaking--------|
                                      |
[GestureIndicator] --thumbs_up/down--> [Session tracker]
                                        |-- save outfit
                                        |-- save reaction
                                        |-- emit to phone
Phone UI
----------------------------------------------
[QueueStatus]   <-scrape_progress
[SessionRecap]  <-session_ended + recap data
```

---

## Cross-Agent Consensus

All 5 research agents converge on these key decisions:

| Decision | Consensus |
|----------|-----------|
| **Architecture** | asyncio event loop with 300ms batched processing |
| **Claude Model** | Haiku 4.5 (`claude-haiku-4-5-20251001`), no beta headers |
| **State Machine** | Minimal 5-state FSM (IDLE/LISTENING/THINKING/SPEAKING/SHOWING_OUTFIT) |
| **Context** | 20k token budget, anchored summaries for compression |
| **Voice Input** | Deepgram Nova-3 in browser, send transcripts via Socket.io |
| **Voice Output** | HeyGen LiveAvatar primary, ElevenLabs/Web Speech fallback |
| **Binary Data** | Base64 JPEG over Socket.io (not WebRTC) |
| **Critical Path** | `orchestrator.py` + `prompts.py` -> everything else builds on this |
| **Cost** | ~$0.02 per 5-min session, ~$2 for 100 hackathon sessions |
| **End-to-End Latency** | ~3.5-4s (voice -> response -> avatar speaking) |
