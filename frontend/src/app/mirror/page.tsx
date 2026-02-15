"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useCamera } from "@/hooks/useCamera";
import { useGestureRecognizer } from "@/hooks/useGestureRecognizer";
import { GestureIndicator } from "@/components/mirror/GestureIndicator";
import ProductCarousel, {
  type ProductCard,
} from "@/components/mirror/ProductCarousel";
import { socket } from "@/lib/socket";
import type { DetectedGesture, GestureType } from "@/types/gestures";

export default function MirrorPageWrapper() {
  return (
    <Suspense fallback={null}>
      <MirrorPage />
    </Suspense>
  );
}

function MirrorPage() {
  const searchParams = useSearchParams();
  const mirrorId =
    searchParams.get("mirror_id") ??
    process.env.NEXT_PUBLIC_MIRROR_ID ??
    "MIRROR-A1";
  const { videoRef, isReady: isCameraReady, error: cameraError } = useCamera();

  // Gesture state
  const [lastGesture, setLastGesture] = useState<GestureType | null>(null);
  const gestureKeyRef = useRef(0);
  const [gestureKey, setGestureKey] = useState(0);

  // Product carousel
  const [products, setProducts] = useState<ProductCard[]>([]);

  // Mirror text overlay from Poke (via send_to_mirror)
  const [mirrorText, setMirrorText] = useState<string | null>(null);
  const mirrorTextTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );

  // --------------- Socket connection ---------------

  useEffect(() => {
    socket.connect();

    socket.emit("join_room", { mirror_id: mirrorId });

    return () => {
      socket.disconnect();
    };
  }, [mirrorId]);

  // --------------- Snapshot handler ---------------

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
      const base64 = dataUrl.split(",")[1];

      socket.emit("mirror_event", {
        type: "snapshot",
        image_base64: base64,
        mirror_id: mirrorId,
      });
    };

    socket.on("request_snapshot", handleSnapshotRequest);
    return () => {
      socket.off("request_snapshot", handleSnapshotRequest);
    };
  }, [videoRef, mirrorId]);

  // --------------- Tool results (product carousel) ---------------

  useEffect(() => {
    const handleToolResult = (data: { type: string; items?: ProductCard[] }) => {
      if (data.type === "clothing_results" && data.items) {
        setProducts(data.items);
      }
    };

    socket.on("tool_result", handleToolResult);
    return () => {
      socket.off("tool_result", handleToolResult);
    };
  }, []);

  // --------------- Mirror text from Poke (via send_to_mirror) ---------------

  useEffect(() => {
    const handleMirrorText = (data: { text: string }) => {
      setMirrorText(data.text);

      // Auto-clear after 15 seconds
      if (mirrorTextTimeoutRef.current) {
        clearTimeout(mirrorTextTimeoutRef.current);
      }
      mirrorTextTimeoutRef.current = setTimeout(
        () => setMirrorText(null),
        15000
      );
    };

    socket.on("mirror_text", handleMirrorText);
    return () => {
      socket.off("mirror_text", handleMirrorText);
      if (mirrorTextTimeoutRef.current) {
        clearTimeout(mirrorTextTimeoutRef.current);
      }
    };
  }, []);

  // --------------- Gesture handling (local carousel only) ---------------

  const handleGesture = useCallback(
    (gesture: DetectedGesture) => {
      console.log(
        "[Mirror] Gesture detected:",
        gesture.type,
        gesture.confidence
      );

      setLastGesture(gesture.type);
      gestureKeyRef.current += 1;
      setGestureKey(gestureKeyRef.current);

      // Animate carousel card locally
      if (products.length > 0) {
        const carouselGesture = (
          window as unknown as Record<string, unknown>
        ).__carouselGesture as ((g: GestureType) => void) | undefined;
        carouselGesture?.(gesture.type);
      }
    },
    [products.length]
  );

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

      {/* Product carousel (bottom) */}
      <ProductCarousel
        items={products}
        onGesture={(gesture, item) => {
          console.log("[Mirror] Carousel gesture:", gesture, item.title);
        }}
      />

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

      {/* Mirror text overlay from Poke */}
      {mirrorText && (
        <div
          style={{
            position: "absolute",
            top: 40,
            left: "50%",
            transform: "translateX(-50%)",
            maxWidth: "80%",
            padding: "16px 24px",
            background: "rgba(0, 0, 0, 0.75)",
            borderRadius: 12,
            color: "#fff",
            fontSize: "1.25rem",
            lineHeight: 1.5,
            textAlign: "center",
            zIndex: 40,
            backdropFilter: "blur(8px)",
          }}
        >
          {mirrorText}
        </div>
      )}

      {/* Mirror ID badge (top-left) */}
      <div
        style={{
          position: "absolute",
          top: 12,
          left: 12,
          padding: "4px 10px",
          background: "rgba(255, 255, 255, 0.15)",
          borderRadius: 6,
          color: "rgba(255, 255, 255, 0.6)",
          fontSize: "0.75rem",
          fontFamily: "monospace",
          zIndex: 50,
        }}
      >
        {mirrorId}
      </div>

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
