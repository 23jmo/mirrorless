# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# Plan: Admin Dashboard — Deepgram Sensitivity + Scrape Job Status

## Context

Two admin dashboard features: (1) expose Deepgram's `endpointing` parameter as a "sensitivity" slider — controls ms of silence before speech is finalized at the phrase level, complementing the existing `utterance_end_ms` which operates at the full-utterance level; (2) show email scraping job status with phase, purchase count, and errors — currently scrape jobs are fire-and-forget ...

### Prompt 2

## Error Type
Console TypeError

## Error Message
Failed to fetch


    at request (src/lib/api.ts:8:21)
    at getAdminQueue (src/lib/api.ts:202:10)
    at AdminPage.useCallback[refresh] (src/app/admin/page.tsx:36:22)
    at AdminPage.useEffect (src/app/admin/page.tsx:55:5)

## Code Frame
   6 |
   7 | async function request<T>(path: string, options?: RequestInit): Promise<T> {
>  8 |   const res = await fetch(`${API_URL}${path}`, {
     |                     ^
   9 |     headers: { "Content-Ty...

### Prompt 3

also add deepgram condfidence threshold toggle

