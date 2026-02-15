# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Railway Deployment Plan

## Context
Railway build is failing with `pip not found` because Railway uses Nixpacks (not raw shell), and the Render-style build command doesn't work. Fix: use Dockerfiles for reliable, portable builds.

## Files to Create (4 files)

### 1. `backend/mcp_server/requirements.txt` — Lean MCP deps
The MCP server only needs 4 packages. No need to install 500MB of rembg/onnxruntime.
```
fastmcp==2.14.5
asyncpg==0.30.0
python-dotenv>=1.1.0
u...

### Prompt 2

ready - do it

