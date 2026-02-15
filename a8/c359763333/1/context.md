# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Plan: Mirror Pose Coordinates for Mirror V2

## Context

The user sees their reflection through a physical two-way mirror (inherently mirrored), but MediaPipe pose landmarks are in raw camera coordinates (not mirrored). When the user leans left, the debug skeleton moves right on screen. The clothing canvas overlay has the same problem. The pose input needs to be mirrored so everything matches the mirror view.

The clothing image pipeline (Gemini flat lay → remb...

### Prompt 2

Okay cool. Can you just commit and push

