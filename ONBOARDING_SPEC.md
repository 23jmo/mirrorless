# Onboarding Flow Spec

## Overview

Wire up the full end-to-end onboarding flow for a **public event booth** (potentially hundreds of users over a day). Users scan a QR code on the mirror, complete onboarding on their phone, wait in a queue, and get an AI styling session at the mirror. The system runs as a continuous kiosk with no manual restarts.

---

## Phone Flow (`/phone`)

### State Machine

```
[check localStorage] → signin → questionnaire → queue → idle → recap
         ↓ (returning user)
        queue
```

### Returning User Detection

- On page load, check `localStorage` for saved `user_id`
- If found, verify user exists in DB via `GET /users/{user_id}`
- If valid → skip straight to **queue** state
- If invalid (deleted, not found) → clear storage, show **signin**
- On successful sign-in, persist `user_id` to `localStorage`

### State: `signin`

First screen after QR scan (new users only).

**Fields:**
- **Name** text input (pre-filled from Google profile after OAuth, editable)
- **Selfie capture**: Camera preview with "Take Photo" button
  - Fallback: "Choose from gallery" file upload if camera permission denied or unsupported
  - Client-side resize to 512x512 JPEG (quality 0.8) before upload
  - Show captured image preview with "Retake" option
  - Selfie is stored as base64 in DB for future avatar generation (not used by Mira now)
- **Google Sign-In** button (reuse existing `GoogleSignIn` component)

**On completion:**
1. Google OAuth completes → user created/retrieved in DB
2. Upload selfie via `POST /auth/selfie`
3. Update profile name via `POST /auth/profile`
4. Trigger Gmail + Calendar scrape via `POST /api/scrape/start` (fire-and-forget, runs in background)
5. Save `user_id` to `localStorage`
6. Transition to `questionnaire`

### State: `questionnaire`

Style questions to inform Mira. Also buys time for background Gmail/Calendar scrape.

**Fields (same as current):**
- Gender: Men / Women / Prefer not to say
- Favorite brands: comma-separated text input
- Style preferences: multi-select chips (Casual, Streetwear, Minimalist, Preppy, Athleisure, Vintage, Smart Casual, Bohemian)
- Occasions: multi-select chips (Everyday, Work, Date Night, Workout, Weekend, Travel)
- Price range: dual sliders ($0-$500, default $0-$300)

**On submit:**
1. Save to `style_profiles` via `POST /api/users/{user_id}/onboarding`
2. Join queue via `POST /queue/join`
3. Transition to `queue`

### State: `queue`

Shows queue position with auto-polling every 5 seconds.

**UI:**
- Queue position number (large, centered)
- "{N} people ahead of you" or "You're next! Hang tight."
- "This page updates automatically."
- When status becomes `active` → transition to `idle`

**Queue timeout:** If the active user doesn't start a mirror session within 2 minutes, they are auto-skipped and the next person advances.

### State: `idle`

Minimal screen shown while user is at the mirror.

**UI:**
- "You're at the mirror!" centered message
- Cycling hardcoded tips/instructions:
  - "Try saying: 'I want something for a night out'"
  - "Give a thumbs up to save items you like"
  - "Swipe left or right to browse outfits"
  - (cycle every ~5 seconds with fade transition)
- Minimal ring timer UI showing approximate session time remaining

**Transition:** Listens for `session_ended` Socket.io event → transition to `recap`

### State: `recap`

Session summary after mirror session ends.

**UI:**
- Session summary text (from `session_ended` event data)
- Liked items count and list
- Session stats (items shown, likes, dislikes)
- **"View on Poke"** button → opens Poke recipe URL in new tab (URL to be provided later, placeholder for now)
- "Done" button → clears state, returns to `signin` (or `queue` if they want another session)

### Design

- Use **Tailwind CSS + shadcn/ui** (already installed for Orb component)
- Replace all current inline styles with Tailwind classes
- Consistent with the existing dark/minimal aesthetic

---

## Mirror Kiosk Mode (`/mirror`)

The mirror runs as a **continuous kiosk** — never needs manual refresh between users.

### Mirror States

```
attract → waiting → session → [attract or waiting]
```

### State: `attract`

Shown when no session is active and no user is queued.

**UI:**
- Mirrorless branding/logo
- QR code linking to the `/phone` Vercel URL
- "Scan to start" prompt
- Orb avatar floating idle (optional, for visual interest)

**Transition:** Mirror polls or listens for queue changes. When a user becomes `active` in queue → transition to `waiting`

### State: `waiting`

A user is active in the queue but their session hasn't started yet.

**UI:**
- "Waiting for [Name]..." message
- **"Start Session" button** — facilitator taps to begin the session for this user
- **"Skip" button** — skip this user, advance to next in queue
- 2-minute countdown timer (auto-skips if timer expires)

**Controls available on:** Both the mirror touchscreen AND the admin page.

**Transition:** "Start Session" tapped (on mirror or admin) → transition to `session`

### State: `session`

Normal Mira session (existing behavior). No changes to session flow.

**Graceful degradation:** If Gmail scrape hasn't finished when session starts, Mira begins with questionnaire data only. If purchases arrive mid-session (scrape completes), the system prompt is rebuilt on the next turn to include them.

**Session limit:** ~20 Claude API calls (current behavior, roughly 3-5 minutes).

**Transition:** Session ends (natural wrap-up, timeout, or force-end from admin) → if next user in queue → `waiting`, else → `attract`

---

## Admin Panel (`/admin`)

Separate frontend route, **no authentication** (anyone with the URL can access).

### Features

1. **Queue List**
   - All users in queue with name, status (waiting/active/completed), position
   - **Skip** button per user (removes from queue)
   - **Reorder** controls (move user up/down in queue)

2. **Current Session**
   - Active user info (name, email)
   - Session stats: API calls used, items shown, likes/dislikes
   - **Force End Session** button

3. **Booth Stats**
   - Total users today
   - Average session length
   - Total items shown/liked across all sessions

4. **Mirror Controls**
   - **Start Session** button (same as mirror's waiting screen)
   - **Skip User** button

---

## Backend Changes

### New Endpoint: `POST /auth/selfie`
- Request: `{ user_id: string, selfie_base64: string }`
- Stores base64 in `users.selfie_base64` column
- Response: updated user profile

### Modified Endpoint: `POST /auth/profile`
- Make `phone` field optional (default `None`)
- Only update phone if provided

### Modified: `backend/scraper/routes.py` — `_background_scrape()`
- After Gmail scrape, also fetch calendar events in parallel
- Use `calendar_fetch.build_calendar_service()` + `fetch_events()` via `run_in_executor()` (synchronous API)
- Store via `scraper.db.store_calendar_events()`
- Calendar failure should not block Gmail scrape completion

### New Migration: `backend/migrations/009_add_selfie_column.sql`
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS selfie_base64 TEXT;
```

### Queue Enhancements
- Auto-advance: when a session ends, mark current queue user as `completed`, advance next to `active`
- 2-minute timeout: background task that checks if active user has started a session
- Socket events for queue changes so mirror can react in real-time
- Reorder endpoint: `PATCH /queue/reorder` for admin drag-and-drop
- Skip endpoint: `DELETE /queue/{user_id}` or `POST /queue/skip/{user_id}`

### Graceful Degradation
- `orchestrator.py` `start_session()` should handle missing purchase data gracefully
- System prompt should note when data is limited: "User completed style questionnaire but purchase history is still loading"
- If scrape completes mid-session, the system prompt rebuild on next turn picks up the new data automatically (already happens — system prompt is rebuilt every turn)

---

## Socket.io Events

### Existing (no changes)
- `session_ended` — emitted to user room, phone listens for recap
- `join_room` — phone joins user room on login

### New Events
- `queue_updated` — emitted to a `mirror` room when queue changes (user added, removed, reordered, advanced)
  - Payload: `{ active_user: { id, name } | null, queue: [{ id, name, position, status }] }`
- `session_force_end` — admin triggers session end
- `queue_user_timeout` — emitted when active user's 2-min timer expires

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| User denies camera permission | Show file upload fallback for selfie |
| Gmail scrape fails | Log error, continue flow — Mira uses questionnaire data only |
| Calendar scrape fails | Silently ignore, not critical |
| User closes phone mid-onboarding | State is lost, they restart on next visit (no partial save) |
| Active queue user doesn't show up | 2-minute timeout, auto-skip to next |
| No one in queue after session ends | Mirror returns to attract screen |
| Multiple tabs open | localStorage sync keeps user consistent |
| Google OAuth fails | Show error message, allow retry |
| Scrape not done when session starts | Mira starts with questionnaire data, incorporates purchases on next turn if they arrive |
| Returning user scans QR again | Skip to queue via localStorage check |

---

## Implementation Priority

1. **Phone onboarding flow** (signin → questionnaire → queue → idle → recap)
2. **Backend: selfie endpoint + calendar scraping + phone optional**
3. **Mirror kiosk mode** (attract → waiting → session cycling)
4. **Queue auto-advance + timeout**
5. **Admin panel**
6. **Tailwind/shadcn styling pass**
