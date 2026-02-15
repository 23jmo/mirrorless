# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Plan: Fix selfie upload 500 error

## Context

The `/auth/selfie` endpoint returns a 500 (Neon HTTP API 400) when called during onboarding. Two root causes:
1. The `selfie_base64` column likely doesn't exist yet (migration `009` not run)
2. Even after migration, the endpoint lacks error handling — a raw httpx exception crashes the server, and because the 500 happens mid-response, Starlette's CORS middleware doesn't add headers, producing a misleading CORS error...

### Prompt 2

can you run it for me

### Prompt 3

I'm first in queue rn but it never moves me out -> i have another tab with the /mirror open but nothing is happening. Shouldn't it be starting my session?

### Prompt 4

i seethis on forntend logs but no start session: IMENSIONS or use PROJECTION_MATRIX.
page.tsx:124 [Mirror] queue_updated: 
Object
active_user
: 
null
queue
: 
Array(6)
0
: 
{id: '0012109d-dab8-4f48-aae1-73b62ee47a76', user_id: 'cee077b2-b367-4b73-8d84-7dcc04cc562c', name: 'Johnathan Y Mo', position: 1, status: 'waiting'}
1
: 
{id: 'dd5697f9-e7c0-4b22-a8ed-254a392ff66b', user_id: 'cee077b2-b367-4b73-8d84-7dcc04cc562c', name: 'Johnathan Y Mo', position: 1, status: 'waiting'}
2
: 
{id: 'bf5ad299-22...

