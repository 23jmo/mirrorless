# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Plan: Session Startup Loading Phase + Fix Speech Cutoffs

## Context

When a mirror session starts, Mira begins talking immediately with no loading screen, sometimes before user data has fully arrived. The opening often gets cut off mid-sentence (likely because STT activates at the same time and the mic picks up Mira's voice from the speakers, triggering an interrupt). The result is a janky, rushed startup where Mira has nothing good to say and then gets interrup...

