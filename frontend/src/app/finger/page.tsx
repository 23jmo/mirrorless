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

      // Position (offset by half width/height to center the dot)
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
