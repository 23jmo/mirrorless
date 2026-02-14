"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useCamera } from "@/hooks/useCamera";
import { useGestureRecognizer } from "@/hooks/useGestureRecognizer";
import { GestureIndicator } from "@/components/mirror/GestureIndicator";
import { socket } from "@/lib/socket";
import type { DetectedGesture, GestureType } from "@/types/gestures";

export default function MirrorPage() {
  const searchParams = useSearchParams();
  const userId = searchParams.get("user_id");
  const { videoRef, isReady: isCameraReady, error: cameraError } = useCamera();
  const [lastGesture, setLastGesture] = useState<GestureType | null>(null);
  const gestureKeyRef = useRef(0);
  const [gestureKey, setGestureKey] = useState(0);

  // Connect socket and join user room
  useEffect(() => {
    socket.connect();

    if (userId) {
      socket.emit("join_room", { user_id: userId });
    }

    return () => {
      socket.disconnect();
    };
  }, [userId]);

  // Listen for snapshot requests from the backend
  useEffect(() => {
    const handleSnapshotRequest = () => {
      const video = videoRef.current;
      if (!video || video.readyState < video.HAVE_CURRENT_DATA) return;

      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.drawImage(video, 0, 0);
      const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
      // Strip the data URL prefix to get raw base64
      const base64 = dataUrl.split(",")[1];

      socket.emit("mirror_event", {
        type: "snapshot",
        image_base64: base64,
        user_id: userId,
      });
    };

    socket.on("request_snapshot", handleSnapshotRequest);
    return () => {
      socket.off("request_snapshot", handleSnapshotRequest);
    };
  }, [videoRef, userId]);

  const handleGesture = useCallback((gesture: DetectedGesture) => {
    console.log("[Mirror] Gesture detected:", gesture.type, gesture.confidence);

    setLastGesture(gesture.type);
    gestureKeyRef.current += 1;
    setGestureKey(gestureKeyRef.current);

    socket.emit("gesture_detected", {
      type: gesture.type,
      confidence: gesture.confidence,
      timestamp: gesture.timestamp,
    });
  }, []);

  const { isLoading: isModelLoading, error: modelError } =
    useGestureRecognizer({
      videoRef,
      isVideoReady: isCameraReady,
      onGesture: handleGesture,
    });

  return (
    <main
      style={{
        position: "relative",
        width: "100vw",
        height: "100vh",
        background: "#000",
        overflow: "hidden",
      }}
    >
      {/* Webcam feed (mirrored) */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: "scaleX(-1)",
        }}
      />

      {/* Gesture visual feedback */}
      <GestureIndicator key={gestureKey} gesture={lastGesture} />

      {/* Status indicators */}
      {(cameraError || modelError) && (
        <div
          style={{
            position: "absolute",
            bottom: 20,
            left: 20,
            color: "#f44",
            fontSize: "1rem",
            zIndex: 30,
          }}
        >
          {cameraError && <div>Camera: {cameraError}</div>}
          {modelError && <div>Model: {modelError}</div>}
        </div>
      )}

      {isModelLoading && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            color: "#fff",
            fontSize: "1.5rem",
            zIndex: 30,
          }}
        >
          Loading gesture recognition...
        </div>
      )}
    </main>
  );
}
