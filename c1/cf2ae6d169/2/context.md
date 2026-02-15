# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Fix: AvatarPiP container ref null + add logging

## Context

After the HeyGen → Memoji migration, clicking "Start Session" logs `[MemojiAvatar] No container ref — cannot start session`. The avatar never initializes.

**Root cause**: React conditional-rendering + ref timing bug.

```
handleSessionActive():
  setSessionActive(true)        ← state queued, NOT yet rendered
  avatar.startSession()         ← runs NOW, containerRef.current is null

JSX:
  {sessi...

### Prompt 2

Can we log all the text-to-speech that we're sending to the fucking agent and all the things that the agent's trying to say? Can we log that in the console logs and in the server logs, or whatever logs? Just put them in logs

### Prompt 3

[MemojiAvatar] startSession: containerRef.current = found
useMemojiAvatar.ts:104 [MemojiAvatar] Session started successfully
useDeepgramSTT.ts:79 [Deprecation] The ScriptProcessorNode is deprecated. Use AudioWorkletNode instead. (https://bit.ly/audio-worklet)
useDeepgramSTT.useCallback[connectWebSocket] @ useDeepgramSTT.ts:79
useDeepgramSTT.ts:122 [STT] Final transcript: Hello?
page.tsx:217 [Mirror] Sending transcript to backend: Hello?
2useDeepgramSTT.ts:122 [STT] Final transcript: Hello?

i sa...

### Prompt 4

[Request interrupted by user for tool use]

