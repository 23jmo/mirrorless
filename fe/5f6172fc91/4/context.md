# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Plan: Add Session Ending Mechanisms

## Context

Sessions currently have no natural ending — they only stop when the API call limit is hit (20 calls), admin force-ends, or socket disconnects. Users can't say "I'm done" and leave, and there's no end button. This plan adds both: a Mira `end_session` tool (so Claude can end the session when the conversation naturally concludes) and a manual "End Session" button on the mirror UI.

---

## Changes

### 1. Add `end_s...

### Prompt 2

push

