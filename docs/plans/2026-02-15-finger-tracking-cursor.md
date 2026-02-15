# Finger Tracking Cursor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a standalone page where the user's index finger controls a cursor and thumb press fires synthetic clicks on DOM elements.

**Architecture:** Custom `useFingerTracking` hook uses MediaPipe HandLandmarker (same `@mediapipe/tasks-vision` already in the project) to detect the right hand's index finger tip (landmark 8) and thumb press (landmarks 3/4). Cursor is a GPU-accelerated `<div>` positioned via refs (no React re-renders). Page at `/finger` with test content.

**Tech Stack:** Next.js, `@mediapipe/tasks-vision` HandLandmarker, React refs for 60fps DOM updates

---

### Task 1: Create the useFingerTracking hook

**Files:**
- Create: `frontend/src/hooks/useFingerTracking.ts`

**Step 1: Write the hook**

This hook follows the same pattern as `useGestureRecognizer.ts` and `usePoseDetection.ts`:
- `FilesetResolver.forVisionTasks` to load WASM
- `HandLandmarker.createFromOptions` with `runningMode: "VIDEO"`, `numHands: 1`
- `requestAnimationFrame` loop calling `detectForVideo`
- Refs for cursor position, press state, hand visibility

```typescript
"use client";

import { useEffect, useRef, useState } from "react";
import { HandLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";

const WASM_URL =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm";
const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";

/** Lerp factor — 0.3 means 30% toward target each frame. */
const LERP = 0.3;

interface UseFingerTrackingOptions {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  isVideoReady: boolean;
}

export interface FingerTrackingResult {
  /** Smoothed cursor X in viewport pixels (ref, not state). */
  cursorXRef: React.RefObject<number>;
  /** Smoothed cursor Y in viewport pixels (ref, not state). */
  cursorYRef: React.RefObject<number>;
  /** Whether thumb is currently pressed down. */
  isPressedRef: React.RefObject<boolean>;
  /** Whether a hand is visible in frame. */
  isHandVisibleRef: React.RefObject<boolean>;
  /** Loading state for the model. */
  isLoading: boolean;
  /** Error message if model fails to load. */
  error: string | null;
}

export function useFingerTracking({
  videoRef,
  isVideoReady,
}: UseFingerTrackingOptions): FingerTrackingResult {
  const cursorXRef = useRef(0);
  const cursorYRef = useRef(0);
  const isPressedRef = useRef(false);
  const isHandVisibleRef = useRef(false);

  // Internal raw target (before lerp)
  const targetXRef = useRef(0);
  const targetYRef = useRef(0);

  const landmarkerRef = useRef<HandLandmarker | null>(null);
  const rafRef = useRef(0);
  const lastVideoTimeRef = useRef(-1);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize HandLandmarker
  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const vision = await FilesetResolver.forVisionTasks(WASM_URL);
        if (cancelled) return;

        const landmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: { modelAssetPath: MODEL_URL, delegate: "GPU" },
          runningMode: "VIDEO",
          numHands: 1,
          minHandDetectionConfidence: 0.5,
          minHandPresenceConfidence: 0.5,
          minTrackingConfidence: 0.5,
        });

        if (cancelled) {
          landmarker.close();
          return;
        }

        landmarkerRef.current = landmarker;
        setIsLoading(false);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load hand model"
          );
          setIsLoading(false);
        }
      }
    }

    init();

    return () => {
      cancelled = true;
      landmarkerRef.current?.close();
      landmarkerRef.current = null;
    };
  }, []);

  // Detection loop
  useEffect(() => {
    if (!isVideoReady || isLoading || !landmarkerRef.current) return;

    function processFrame() {
      const video = videoRef.current;
      const landmarker = landmarkerRef.current;

      if (!video || !landmarker || video.readyState < 2) {
        rafRef.current = requestAnimationFrame(processFrame);
        return;
      }

      // Skip duplicate frames
      if (video.currentTime === lastVideoTimeRef.current) {
        rafRef.current = requestAnimationFrame(processFrame);
        return;
      }
      lastVideoTimeRef.current = video.currentTime;

      const now = performance.now();
      const result = landmarker.detectForVideo(video, now);

      if (result.landmarks.length > 0 && result.landmarks[0].length > 0) {
        const hand = result.landmarks[0];
        isHandVisibleRef.current = true;

        // Index finger tip = landmark 8
        const indexTip = hand[8];
        // MediaPipe normalizes 0–1. Map to viewport.
        // X is mirrored by default in MediaPipe, so (1 - x) gives natural mapping
        targetXRef.current = (1 - indexTip.x) * window.innerWidth;
        targetYRef.current = indexTip.y * window.innerHeight;

        // Thumb press: landmark 4 (thumb tip) y > landmark 3 (thumb IP) y
        const thumbTip = hand[4];
        const thumbIP = hand[3];
        isPressedRef.current = thumbTip.y > thumbIP.y;
      } else {
        isHandVisibleRef.current = false;
      }

      // Lerp smoothing
      cursorXRef.current += (targetXRef.current - cursorXRef.current) * LERP;
      cursorYRef.current += (targetYRef.current - cursorYRef.current) * LERP;

      rafRef.current = requestAnimationFrame(processFrame);
    }

    rafRef.current = requestAnimationFrame(processFrame);

    return () => {
      cancelAnimationFrame(rafRef.current);
    };
  }, [isVideoReady, isLoading, videoRef]);

  return {
    cursorXRef,
    cursorYRef,
    isPressedRef,
    isHandVisibleRef,
    isLoading,
    error,
  };
}
```

**Step 2: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit src/hooks/useFingerTracking.ts 2>&1 || echo "check errors"`

The file should have no TypeScript errors. If there are import issues with `@mediapipe/tasks-vision`, just verify `HandLandmarker` is exported (it is in the version the project uses).

**Step 3: Commit**

```bash
git add frontend/src/hooks/useFingerTracking.ts
git commit -m "feat: add useFingerTracking hook for cursor control"
```

---

### Task 2: Create the /finger page

**Files:**
- Create: `frontend/src/app/finger/page.tsx`

**Step 1: Write the page**

The page:
- Uses `useCamera()` to get webcam (hidden `<video>`)
- Uses `useFingerTracking()` to get cursor position + press state
- Renders a cursor `<div>` updated via refs in a rAF loop (no React re-renders)
- Handles thumb-press transitions (up→down = click, visual feedback)
- Shows test content: 6 colored boxes that respond to clicks

```tsx
"use client";

import { useEffect, useRef, useCallback } from "react";
import { useCamera } from "@/hooks/useCamera";
import { useFingerTracking } from "@/hooks/useFingerTracking";

const TEST_BOXES = [
  { id: 1, color: "#e74c3c", label: "Red" },
  { id: 2, color: "#3498db", label: "Blue" },
  { id: 3, color: "#2ecc71", label: "Green" },
  { id: 4, color: "#f39c12", label: "Orange" },
  { id: 5, color: "#9b59b6", label: "Purple" },
  { id: 6, color: "#1abc9c", label: "Teal" },
];

export default function FingerPage() {
  const { videoRef, isReady: isCameraReady, error: cameraError } = useCamera();
  const {
    cursorXRef,
    cursorYRef,
    isPressedRef,
    isHandVisibleRef,
    isLoading,
    error: trackingError,
  } = useFingerTracking({ videoRef, isVideoReady: isCameraReady });

  const cursorRef = useRef<HTMLDivElement>(null);
  const renderRafRef = useRef(0);
  const wasPressedRef = useRef(false);

  // Render loop: update cursor DOM + handle click transitions
  useEffect(() => {
    function renderLoop() {
      const cursor = cursorRef.current;
      if (!cursor) {
        renderRafRef.current = requestAnimationFrame(renderLoop);
        return;
      }

      const visible = isHandVisibleRef.current;
      const pressed = isPressedRef.current;
      const x = cursorXRef.current;
      const y = cursorYRef.current;

      // Show/hide cursor
      cursor.style.opacity = visible ? "1" : "0";

      // Position
      cursor.style.transform = `translate(${x - 7}px, ${y - 7}px)`;

      // Color feedback: white normally, red when pressed
      cursor.style.background = pressed ? "#ff4444" : "#ffffff";
      cursor.style.boxShadow = pressed
        ? "0 0 12px 4px rgba(255, 68, 68, 0.6)"
        : "0 0 10px 2px rgba(255, 255, 255, 0.4)";

      // Click detection: fire on press-down transition
      if (pressed && !wasPressedRef.current && visible) {
        const el = document.elementFromPoint(x, y);
        if (el) {
          el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        }
      }
      wasPressedRef.current = pressed;

      renderRafRef.current = requestAnimationFrame(renderLoop);
    }

    renderRafRef.current = requestAnimationFrame(renderLoop);

    return () => {
      cancelAnimationFrame(renderRafRef.current);
    };
  }, [cursorXRef, cursorYRef, isPressedRef, isHandVisibleRef]);

  const handleBoxClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const target = e.currentTarget;
      // Visual feedback: scale bounce
      target.style.transform = "scale(1.15)";
      // Increment counter
      const counter = target.querySelector("[data-counter]");
      if (counter) {
        const count = parseInt(counter.textContent || "0", 10) + 1;
        counter.textContent = String(count);
      }
      setTimeout(() => {
        target.style.transform = "scale(1)";
      }, 200);
    },
    []
  );

  const err = cameraError || trackingError;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "#111",
        overflow: "hidden",
      }}
    >
      {/* Hidden video for camera feed */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{ position: "absolute", opacity: 0, pointerEvents: "none" }}
      />

      {/* Status */}
      {(isLoading || err) && (
        <div
          style={{
            position: "absolute",
            top: 20,
            left: 20,
            color: err ? "#ff4444" : "#888",
            fontFamily: "monospace",
            fontSize: 14,
            zIndex: 100,
          }}
        >
          {err ? `Error: ${err}` : "Loading hand tracking model..."}
        </div>
      )}

      {/* Test content: clickable boxes */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 32,
          padding: 64,
          height: "100%",
          boxSizing: "border-box",
        }}
      >
        {TEST_BOXES.map((box) => (
          <div
            key={box.id}
            onClick={handleBoxClick}
            style={{
              background: box.color,
              borderRadius: 16,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              transition: "transform 0.2s ease",
              userSelect: "none",
            }}
          >
            <span style={{ fontSize: 32, fontWeight: 700, color: "#fff" }}>
              {box.label}
            </span>
            <span
              data-counter
              style={{
                fontSize: 48,
                fontWeight: 800,
                color: "rgba(255,255,255,0.9)",
                marginTop: 8,
              }}
            >
              0
            </span>
          </div>
        ))}
      </div>

      {/* Cursor dot */}
      <div
        ref={cursorRef}
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: "#ffffff",
          boxShadow: "0 0 10px 2px rgba(255, 255, 255, 0.4)",
          pointerEvents: "none",
          zIndex: 9999,
          opacity: 0,
          transition: "background 0.1s, box-shadow 0.1s",
        }}
      />
    </div>
  );
}
```

**Step 2: Verify it builds**

Run: `cd frontend && npx next build 2>&1 | tail -20`

Or quicker: `cd frontend && npx tsc --noEmit 2>&1 | head -20`

**Step 3: Commit**

```bash
git add frontend/src/app/finger/page.tsx
git commit -m "feat: add /finger page with finger tracking cursor and test content"
```

---

### Task 3: Manual browser test and tuning

**Step 1: Start dev server**

Run: `cd frontend && npm run dev`

**Step 2: Open browser and test**

Open `http://localhost:3000/finger` in Chrome. Verify:
1. Camera permission prompt appears and camera activates
2. Hand tracking model loads (loading message disappears)
3. Cursor dot appears when hand is in frame
4. Cursor follows index finger tip smoothly
5. Cursor hides when hand leaves frame
6. Thumb press changes cursor from white to red
7. Thumb press triggers click on the colored box under the cursor (counter increments)
8. Cursor movement feels responsive (not laggy or jittery)

**Step 3: Tune if needed**

Likely tuning points:
- `LERP` constant (0.3) — increase for snappier, decrease for smoother
- X-axis mirroring — if cursor moves opposite to finger, toggle the `(1 - indexTip.x)` to just `indexTip.x`
- Thumb detection threshold — if clicks are too sensitive or not sensitive enough, may need to add a y-distance threshold instead of pure comparison

**Step 4: Commit any tuning changes**

```bash
git add -A
git commit -m "fix: tune finger tracking parameters"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | useFingerTracking hook | `frontend/src/hooks/useFingerTracking.ts` |
| 2 | /finger page with cursor + test content | `frontend/src/app/finger/page.tsx` |
| 3 | Manual browser test + tuning | Adjustments to above files |

**Total new files:** 2
**Modified files:** 0
**Dependencies:** None (uses existing `@mediapipe/tasks-vision`)
