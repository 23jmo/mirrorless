# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Orb Avatar: Replace Memoji with ElevenLabs Orb + Streaming TTS

## Context

The current avatar system uses pre-recorded Memoji video loops (6 states) + 13 scripted response videos with per-sentence TTS fetching. It's complex, glitchy (blob URL crashes), and requires ~5MB of video assets. We're replacing the entire visual + audio pipeline with:

1. **ElevenLabs UI Orb** — 3D WebGL sphere (`@elevenlabs/cli` component) that reacts to audio volume
2. **Streaming TT...

### Prompt 2

<task-notification>
<task-id>ae2a8fe</task-id>
<status>completed</status>
<summary>Agent "Research ElevenLabs streaming TTS" completed</summary>
<result>Here is the complete research on ElevenLabs streaming TTS. There are two approaches, and I have real code for both.

---

## Two Approaches

### Approach 1: REST Streaming (Simpler -- Recommended for Mirrorless)

**Endpoint:** `POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream`

Uses standard `fetch` with `response.body.getReade...

### Prompt 3

does streaming tts make it faster?

### Prompt 4

okay commit and push your changes

