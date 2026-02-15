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
        // X is mirrored: (1 - x) so moving finger right moves cursor right
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
