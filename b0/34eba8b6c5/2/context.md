# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Plan: Fix `start_session` 400 crash — invalid UUID for demo user

## Context

When clicking "Start Session" on the `/chat` page, the backend crashes with `400 Bad Request` from Neon. The frontend sends `user_id = "chat-demo-user"` (hardcoded at `chat/page.tsx:31`), but `users.id` is type `uuid` — Neon rejects the non-UUID string at query time. Even with a valid UUID, the session `INSERT` would fail if no matching user exists (FK constraint on `sessions.user_i...

### Prompt 2

show me exactly what the systme prompt is to mira - what context is she given, what tools can she call?

### Prompt 3

can we lowk show the entire system prompt in the chat i want to see for debugging purposes

### Prompt 4

Make sure mira always starts with a direct roast on some niche shopping / purchase history of the user. By the way, I'm noticing that some of the purchases we include are pretty not clothing related. Does mira have tool to search for stuff? What framework are we using to build Mira? Are we using claude agents sdk?

### Prompt 5

Make her also constantly reference previous purchases

### Prompt 6

can you research whether or not we are implementing this optimally? spin up a few agents to research this.

### Prompt 7

Yeah can you fix all the issues you mentioned, spin up a separate agent for the scraper fix tho

### Prompt 8

[Request interrupted by user for tool use]

