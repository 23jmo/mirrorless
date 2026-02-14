"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useCamera } from "@/hooks/useCamera";
import { useGestureRecognizer } from "@/hooks/useGestureRecognizer";
import { usePoseDetection } from "@/hooks/usePoseDetection";
import { GestureIndicator } from "@/components/mirror/GestureIndicator";
import { ClothingOverlay } from "@/components/mirror/ClothingOverlay";
import { MiraAvatar, type OccupiedRegion } from "@/components/mirror/MiraAvatar";
import { SparkleTransition } from "@/components/mirror/SparkleTransition";
import { OutfitInfoPanel } from "@/components/mirror/OutfitInfoPanel";
import { IdleScreen } from "@/components/mirror/IdleScreen";
import { captureBase64Snapshot } from "@/lib/camera-snapshot";
import { computeAffineTransform } from "@/lib/pose-overlay";
import { socket } from "@/lib/socket";
import type { DetectedGesture, GestureType } from "@/types/gestures";
import type { PoseResult } from "@/types/pose";
import type { OutfitRecommendation } from "@/types/outfit";

const SCREEN_WIDTH = 1920;
const SCREEN_HEIGHT = 1080;
const DEFAULT_PHONE_PATH = "/phone";

export default function MirrorPage() {
  const { videoRef, isReady: isCameraReady, error: cameraError } = useCamera();

  // Phone URL — resolve on client to avoid hydration mismatch
  const [phoneUrl, setPhoneUrl] = useState("");
  useEffect(() => {
    setPhoneUrl(
      process.env.NEXT_PUBLIC_PHONE_URL ||
        `${window.location.origin}${DEFAULT_PHONE_PATH}`
    );
  }, []);

  // Gesture state
  const [lastGesture, setLastGesture] = useState<GestureType | null>(null);
  const gestureKeyRef = useRef(0);
  const [gestureKey, setGestureKey] = useState(0);

  // Pose state
  const [currentPose, setCurrentPose] = useState<PoseResult | null>(null);

  // Outfit state
  const [currentOutfit, setCurrentOutfit] = useState<OutfitRecommendation | null>(null);
  const [showSparkle, setShowSparkle] = useState(false);
  const [sparkleKey, setSparkleKey] = useState(0);
  const [showInfoPanel, setShowInfoPanel] = useState(false);
  const [infoPanelKey, setInfoPanelKey] = useState(0);

  // Session state
  const [sessionActive, setSessionActive] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);

  // Occupied regions for avatar collision avoidance
  const [occupiedRegions, setOccupiedRegions] = useState<OccupiedRegion[]>([]);

  // Connect socket on mount
  useEffect(() => {
    socket.connect();

    socket.on("outfit_recommendation", (data: OutfitRecommendation) => {
      setSparkleKey((k) => k + 1);
      setShowSparkle(true);
      setTimeout(() => {
        setCurrentOutfit(data);
        setShowSparkle(false);
      }, 400);
    });

    socket.on("session_status", (data: { status: string; user_id: string }) => {
      if (data.status === "active") {
        setSessionActive(true);
        setUserId(data.user_id);
        socket.emit("join_room", { user_id: data.user_id });
        socket.emit("session_ready", { user_id: data.user_id });
      } else if (data.status === "completed" || data.status === "ended") {
        setSessionActive(false);
        setCurrentOutfit(null);
        setCurrentPose(null);
        setUserId(null);
      }
    });

    socket.on("request_snapshot", () => {
      if (videoRef.current) {
        const base64 = captureBase64Snapshot(videoRef.current, 0.7);
        socket.emit("camera_snapshot", {
          user_id: userId,
          image_base64: base64,
          timestamp: performance.now(),
        });
      }
    });

    socket.on("show_outfit_info", () => {
      setInfoPanelKey((k) => k + 1);
      setShowInfoPanel(true);
    });

    return () => {
      socket.off("outfit_recommendation");
      socket.off("session_status");
      socket.off("request_snapshot");
      socket.off("show_outfit_info");
      socket.disconnect();
    };
  }, [userId, videoRef]);

  // Gesture handler
  const handleGesture = useCallback(
    (gesture: DetectedGesture) => {
      console.log("[Mirror] Gesture:", gesture.type, gesture.confidence);

      setLastGesture(gesture.type);
      gestureKeyRef.current += 1;
      setGestureKey(gestureKeyRef.current);

      socket.emit("gesture_detected", {
        type: gesture.type,
        confidence: gesture.confidence,
        timestamp: gesture.timestamp,
      });

      // Show info panel on thumbs up
      if (gesture.type === "thumbs_up") {
        setInfoPanelKey((k) => k + 1);
        setShowInfoPanel(true);
      }
    },
    []
  );

  // Pose handler — update overlay positions
  const handlePoseUpdate = useCallback((result: PoseResult) => {
    setCurrentPose(result);

    // Update occupied regions for avatar collision avoidance
    if (currentOutfit) {
      const regions: OccupiedRegion[] = [];
      for (const item of currentOutfit.items) {
        const transform = computeAffineTransform(
          result.landmarks,
          item.category,
          SCREEN_WIDTH,
          SCREEN_HEIGHT
        );
        if (transform) {
          regions.push({
            x: transform.x - transform.width / 2,
            y: transform.y - transform.height / 2,
            width: transform.width,
            height: transform.height,
          });
        }
      }
      setOccupiedRegions(regions);
    }
  }, [currentOutfit]);

  const { isLoading: isModelLoading, error: modelError } =
    useGestureRecognizer({
      videoRef,
      isVideoReady: isCameraReady,
      onGesture: handleGesture,
    });

  const { isLoading: isPoseLoading, error: poseError } = usePoseDetection({
    videoRef,
    isVideoReady: isCameraReady,
    onPoseUpdate: handlePoseUpdate,
  });

  // Show idle screen when no session
  if (!sessionActive) {
    return (
      <main style={{ width: "100vw", height: "100vh", background: "#000" }}>
        {phoneUrl && <IdleScreen qrUrl={phoneUrl} />}
      </main>
    );
  }

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
      {/* Hidden video element for pose/gesture detection */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: 1,
          height: 1,
          opacity: 0,
          pointerEvents: "none",
        }}
      />

      {/* Clothing overlay canvas */}
      <ClothingOverlay
        pose={currentPose}
        outfit={currentOutfit}
        width={SCREEN_WIDTH}
        height={SCREEN_HEIGHT}
      />

      {/* Sparkle transition */}
      <SparkleTransition key={sparkleKey} active={showSparkle} />

      {/* Mira avatar */}
      <MiraAvatar
        occupiedRegions={occupiedRegions}
        screenWidth={SCREEN_WIDTH}
        screenHeight={SCREEN_HEIGHT}
      />

      {/* Gesture feedback */}
      <GestureIndicator key={gestureKey} gesture={lastGesture} />

      {/* Outfit info panel */}
      <OutfitInfoPanel
        key={infoPanelKey}
        outfit={currentOutfit}
        visible={showInfoPanel}
      />

      {/* Status indicators */}
      {(cameraError || modelError || poseError) && (
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
          {modelError && <div>Gesture Model: {modelError}</div>}
          {poseError && <div>Pose Model: {poseError}</div>}
        </div>
      )}

      {(isModelLoading || isPoseLoading) && (
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
          Loading models...
        </div>
      )}
    </main>
  );
}
