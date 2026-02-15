# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Fix: Avatar doesn't speak Mira's responses

## Context

The LiveAvatar SDK migration is complete (SDK installed, hook created, mirror page wired, backend token endpoint updated). But the avatar **never speaks** — despite Deepgram picking up user speech and Mira (the orchestrator) generating responses via Claude. The pipeline breaks in two places.

## Root Cause Analysis

### Bug 1: Backend never signals end-of-message (CRITICAL)

**File**: `backend/agent/orches...

### Prompt 2

I SEE THIS GUYS FACE BUT HE'S JUST STARING AT ME. can you research the liveavatar sdk docs?

### Prompt 3

[Request interrupted by user for tool use]

