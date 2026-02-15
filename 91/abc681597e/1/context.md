# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Plan: Fix QR Code URLs

## Context

Two QR codes need to be configured correctly:

1. **Attract screen QR code** — should point to the phone onboarding flow at `https://mirrorless.vercel.app/phone` (the user scans this to join the queue)
2. **Session recap QR code** — should point to Poke at `https://poke.com/r/fU6M2CeFtp6` (after session ends, user scans this to continue shopping with their AI stylist)

Currently, the attract screen QR was mistakenly changed...

### Prompt 2

A quick question: how are we doing the auth for Poke's MCP? Shouldn't we be doing auth via their phone number? Shouldn't we take in their phone number during the onboarding form? Otherwise how do we link sessions to a Poke?

### Prompt 3

[Request interrupted by user for tool use]

