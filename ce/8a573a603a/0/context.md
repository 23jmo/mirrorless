# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Plan: Make Pose Debug Overlay Visible in Mirror-V2

## Context

The user wants to verify MediaPipe body tracking is working in `/mirror-v2` by seeing skeleton/landmark points on a black background. All the infrastructure already exists — `usePoseDetection` runs in all kiosk states, and `DebugOverlay` toggles with the `d` key — but the skeleton is **invisible** because the DebugOverlay wrapper is at `z-index: 6` while the attract/waiting state overlays sit at ...

