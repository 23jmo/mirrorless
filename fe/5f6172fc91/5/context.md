# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Plan: Next.js API Routes for Phone Flow (Auth + Queue)

## Context

The phone onboarding flow (Google sign-in → queue → wait) currently calls the Python backend at `NEXT_PUBLIC_API_URL` (`localhost:8000`). This works on the developer's computer but fails on phones accessing `mirrorless.vercel.app` because `localhost:8000` doesn't exist on the phone. The backend is difficult to deploy to Render right now.

**Solution:** Create Next.js API routes (`app/api/*/ro...

### Prompt 2

can we push and deploy to vercel

