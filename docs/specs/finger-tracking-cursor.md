# Finger Tracking Cursor — Spec

## Goal

Browser-based finger tracking on a standalone page. The user's index finger tip controls a cursor on screen, and pressing the thumb down fires a synthetic click on whatever DOM element is under the cursor. Camera feed is hidden.

## Page

- **Route:** New page at `/finger` (or `/finger-demo`)
- **Content:** Dark background with several clickable test elements (colored buttons, boxes) to verify click detection works
- **No camera feed visible** — camera runs in background for hand tracking only

## Finger Tracking

**Technology:** Google MediaPipe Hands via `@mediapipe/tasks-vision` (HandLandmarker) — matches the existing codebase pattern.

**Hand:** Right hand only. Ignore left hand entirely. If MediaPipe returns results, use the first detected hand (assume right).

**Landmark:** Index finger tip = landmark 8 (of 21 hand landmarks).

**Coordinate mapping:**
- MediaPipe returns normalized coordinates (0.0–1.0) relative to the camera frame
- Map directly to viewport: `x * window.innerWidth`, `y * window.innerHeight`
- The camera feed is already horizontally flipped by MediaPipe's mirror mode — the finger acts like a mouse, cursor follows wherever it goes
- No additional axis flipping needed

**Frame rate:** Process hand landmarks every frame from the webcam using `requestAnimationFrame` or MediaPipe's video callback. Camera at default resolution (likely 720p).

## Cursor

**Appearance:** Simple circle, 14px diameter, white (`#ffffff`) with a subtle glow (`box-shadow`). Rendered as an absolutely-positioned `<div>` with `pointer-events: none` and high `z-index`.

**Positioning:** Updated every frame via `transform: translate(x, y)` for GPU-accelerated movement. No React state updates for cursor position — use a ref and direct DOM manipulation for 60fps.

**Smoothing:** Simple linear interpolation (lerp) between current and target position. Factor ~0.3 (30% of the way each frame). Enough to reduce jitter without feeling laggy.

**When hand leaves frame:** Cursor hides immediately (opacity: 0 or display: none). Reappears at the new position when hand returns.

## Clicking (Thumb Press)

**Gesture:** Thumb tip (landmark 4) y-coordinate > thumb IP joint (landmark 3) y-coordinate in normalized camera coordinates = thumb pressed down.

**Detection:**
- Track previous thumb state (up/down) each frame
- Transition from up → down: fire `mousedown` event, then `click` event via `document.elementFromPoint(cursorX, cursorY)`
- Thumb stays down: no repeat clicks (single click on transition only)
- Transition from down → up: fire `mouseup` event (optional, for future drag support)

**Synthetic click implementation:**
```
const el = document.elementFromPoint(cursorX, cursorY)
if (el) el.click()
```

**Visual feedback:** Cursor changes color from white to a highlight color (e.g. `#ff4444` red or `#00ff88` green) while thumb is pressed. Returns to white when thumb is released.

## Architecture

**Hook:** `useFingerTracking(videoRef)` — a custom React hook that:
- Takes a `<video>` ref (webcam feed)
- Initializes HandLandmarker from `@mediapipe/tasks-vision`
- Runs detection loop via `requestAnimationFrame`
- Returns: `{ cursorX, cursorY, isPressed, isHandVisible }` as refs (not state, for performance)
- Cleans up on unmount

**Page component:** `/finger/page.tsx`
- Requests camera access, pipes to hidden `<video>` element
- Renders cursor `<div>` and test content
- Uses `useFingerTracking` hook
- Animation loop reads refs and updates cursor DOM directly

## Test Content

Several interactive elements on the page to verify clicking works:
- 4-6 colored boxes/buttons spread across the screen
- Each shows a visual change when clicked (e.g. counter increment, color change, or "Clicked!" text)
- Demonstrates that synthetic clicks properly target the correct element based on cursor position

## Dependencies

- `@mediapipe/tasks-vision` — already in the project (used by `useGestureRecognizer`)
- No new dependencies needed

## What This Does NOT Include

- No gun gesture detection (no StickyGunDetector)
- No head tilt / body movement controls
- No left hand tracking
- No dual-threaded cursor architecture (browser single-thread with rAF is sufficient)
- No pointer lock / game integration
- No connection to the existing mirror page or Mira session
- No socket.io events
