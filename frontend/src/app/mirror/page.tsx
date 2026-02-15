"use client";

import { Suspense } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useCamera } from "@/hooks/useCamera";
import { useGestureRecognizer } from "@/hooks/useGestureRecognizer";
import { usePoseDetection } from "@/hooks/usePoseDetection";
import { useLiveAvatar } from "@/hooks/useLiveAvatar";
import { useDeepgramSTT } from "@/hooks/useDeepgramSTT";
import { GestureIndicator } from "@/components/mirror/GestureIndicator";
import { ClothingCanvas } from "@/components/mirror/ClothingCanvas";
import AvatarPiP from "@/components/mirror/AvatarPiP";
import VoiceIndicator from "@/components/mirror/VoiceIndicator";
import ProductCarousel, {
  type ProductCard,
} from "@/components/mirror/ProductCarousel";
import { SentenceBuffer } from "@/lib/sentence-buffer";
import { socket } from "@/lib/socket";
import type { DetectedGesture, GestureType } from "@/types/gestures";
import type { PoseResult } from "@/types/pose";
import type { ClothingItem } from "@/types/clothing";
import { mapToClothingItems } from "@/lib/map-clothing-items";

export default function MirrorPageWrapper() {
  return (
    <Suspense fallback={null}>
      <MirrorPage />
    </Suspense>
  );
}

function MirrorPage() {
  const searchParams = useSearchParams();
  const userId = searchParams.get("user_id");

  // Camera + gesture recognition
  const { videoRef, isReady: isCameraReady, error: cameraError } = useCamera();
  const [lastGesture, setLastGesture] = useState<GestureType | null>(null);
  const gestureKeyRef = useRef(0);
  const [gestureKey, setGestureKey] = useState(0);

  // Session state
  const [sessionActive, setSessionActive] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [products, setProducts] = useState<ProductCard[]>([]);
  const [voiceMessage, setVoiceMessage] = useState<{ text: string; emotion: string } | null>(null);

  // Pose detection + clothing overlay state
  const [currentPose, setCurrentPose] = useState<PoseResult | null>(null);

  interface CanvasOutfit {
    name: string;
    items: ClothingItem[];
  }
  const [canvasOutfits, setCanvasOutfits] = useState<CanvasOutfit[]>([]);
  const [canvasOutfitIndex, setCanvasOutfitIndex] = useState(0);
  const activeCanvasOutfit = canvasOutfits[canvasOutfitIndex]?.items ?? [];

  // Avatar + voice
  const avatar = useLiveAvatar();
  const stt = useDeepgramSTT();

  // Queue transcripts while avatar is speaking, send when quiet
  const pendingTranscriptRef = useRef<string | null>(null);

  // Sentence buffer: accumulates streamed speech chunks → fires complete sentences to avatar
  const sentenceBuffer = useMemo(
    () =>
      new SentenceBuffer((sentence) => {
        avatar.speak(sentence);
      }),
    // avatar.speak is stable (useCallback), safe to depend on
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [avatar.speak],
  );

  // Pose detection for clothing overlay
  const handlePoseUpdate = useCallback((result: PoseResult) => {
    setCurrentPose(result);
  }, []);

  usePoseDetection({
    videoRef,
    isVideoReady: isCameraReady,
    onPoseUpdate: handlePoseUpdate,
  });

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

  // Listen for session_active from backend
  useEffect(() => {
    const handleSessionActive = () => {
      setSessionActive(true);
      setIsStarting(false);
      setCanvasOutfits([]);
      setCanvasOutfitIndex(0);
      avatar.startSession();
      stt.startListening();
    };

    socket.on("session_active", handleSessionActive);
    return () => {
      socket.off("session_active", handleSessionActive);
    };
    // avatar.startSession and stt.startListening are stable refs
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Listen for mira_speech events (streamed text from AI)
  useEffect(() => {
    const handleSpeech = (data: { text?: string; is_chunk?: boolean }) => {
      // Fallback session detection: if we get speech before session_active
      if (!sessionActive && !isStarting) {
        setSessionActive(true);
        setIsStarting(false);
        avatar.startSession();
        stt.startListening();
      }

      if (data.text) {
        if (data.is_chunk === false) {
          // End of message — flush remaining buffer
          sentenceBuffer.feed(data.text);
          sentenceBuffer.flush();
        } else {
          sentenceBuffer.feed(data.text);
        }
      }
    };

    socket.on("mira_speech", handleSpeech);
    return () => {
      socket.off("mira_speech", handleSpeech);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionActive, isStarting, sentenceBuffer]);

  // Listen for tool_result events (product recommendations + voice messages)
  useEffect(() => {
    const handleToolResult = (data: {
      type?: string;
      tool?: string;
      items?: ProductCard[];
      text?: string;
      emotion?: string;
      outfit_name?: string;
    }) => {
      // display_product: flat lay items from Gemini pipeline
      if (data.type === "display_product" && data.items) {
        const clothingItems = mapToClothingItems(data.items);
        if (clothingItems.length > 0) {
          setCanvasOutfits((prev) => {
            const next = [...prev, { name: data.outfit_name || `Outfit ${prev.length + 1}`, items: clothingItems }];
            setCanvasOutfitIndex(next.length - 1); // auto-switch to latest
            return next;
          });
        }
        setProducts(data.items); // keep card display too
        return;
      }
      // voice_message: text for TTS / display
      if (data.type === "voice_message" && data.text) {
        setVoiceMessage({ text: data.text, emotion: data.emotion ?? "neutral" });
        avatar.speak(data.text);
        return;
      }
      // Legacy: present_items / clothing_results
      if ((data.type === "clothing_results" || data.tool === "present_items") && data.items) {
        setProducts(data.items);
      }
    };

    socket.on("tool_result", handleToolResult);
    return () => {
      socket.off("tool_result", handleToolResult);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [avatar.speak]);

  // Listen for session_ended
  useEffect(() => {
    const handleSessionEnded = () => {
      avatar.stopSession();
      stt.stopListening();
      setSessionActive(false);
      setProducts([]);
      setCanvasOutfits([]);
      setCanvasOutfitIndex(0);
    };

    socket.on("session_ended", handleSessionEnded);
    return () => {
      socket.off("session_ended", handleSessionEnded);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Send transcripts to backend when avatar stops speaking
  useEffect(() => {
    if (!avatar.isSpeaking && pendingTranscriptRef.current && userId) {
      socket.emit("mirror_event", {
        user_id: userId,
        event: { type: "voice", transcript: pendingTranscriptRef.current },
      });
      pendingTranscriptRef.current = null;
    }
  }, [avatar.isSpeaking, userId]);

  // Forward final STT transcripts
  useEffect(() => {
    if (!stt.transcript || !userId) return;

    if (avatar.isSpeaking) {
      // Queue transcript until avatar is done speaking to avoid interruption
      pendingTranscriptRef.current = stt.transcript;
    } else {
      socket.emit("mirror_event", {
        user_id: userId,
        event: { type: "voice", transcript: stt.transcript },
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stt.transcript, userId]);

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

  // Gesture handler
  const handleGesture = useCallback(
    (gesture: DetectedGesture) => {
      console.log("[Mirror] Gesture detected:", gesture.type, gesture.confidence);

      setLastGesture(gesture.type);
      gestureKeyRef.current += 1;
      setGestureKey(gestureKeyRef.current);

      // Navigate canvas outfits with swipe gestures
      if (canvasOutfits.length > 1) {
        if (gesture.type === "swipe_left") {
          setCanvasOutfitIndex((i) => (i + 1) % canvasOutfits.length);
        } else if (gesture.type === "swipe_right") {
          setCanvasOutfitIndex((i) => (i - 1 + canvasOutfits.length) % canvasOutfits.length);
        }
      }

      // Forward to carousel if it exists
      const carouselGesture = (
        window as unknown as Record<string, unknown>
      ).__carouselGesture as ((g: GestureType) => void) | undefined;
      if (carouselGesture) {
        carouselGesture(gesture.type);
      }

      socket.emit("mirror_event", {
        user_id: userId,
        event: {
          type: "gesture",
          gesture: gesture.type,
          confidence: gesture.confidence,
          timestamp: gesture.timestamp,
        },
      });
    },
    [userId, canvasOutfits.length],
  );

  const { isLoading: isModelLoading, error: modelError } =
    useGestureRecognizer({
      videoRef,
      isVideoReady: isCameraReady,
      onGesture: handleGesture,
    });

  const handleProductGesture = useCallback(
    (gesture: GestureType, item: ProductCard) => {
      socket.emit("mirror_event", {
        user_id: userId,
        event: {
          type: "product_gesture",
          gesture,
          product_id: item.product_id,
          title: item.title,
        },
      });
    },
    [userId],
  );

  const handleStartSession = useCallback(() => {
    if (!userId || isStarting || sessionActive) return;

    // Unlock browser audio policy while we still have the user gesture context.
    // When session.attach() later calls play(), the browser will allow it.
    const ctx = new AudioContext();
    ctx.resume().then(() => ctx.close());

    setIsStarting(true);
    socket.emit("start_session", { user_id: userId });
  }, [userId, isStarting, sessionActive]);

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

      {/* Clothing overlay canvas */}
      {activeCanvasOutfit.length > 0 && currentPose && (
        <ClothingCanvas
          pose={currentPose}
          items={activeCanvasOutfit}
          width={1920}
          height={1080}
        />
      )}

      {/* Outfit dot indicator */}
      {canvasOutfits.length > 1 && (
        <div style={{ position: "absolute", bottom: 20, left: "50%", transform: "translateX(-50%)", display: "flex", gap: 8, zIndex: 18 }}>
          {canvasOutfits.map((_, i) => (
            <div key={i} style={{
              width: 10, height: 10, borderRadius: "50%",
              background: i === canvasOutfitIndex ? "#fff" : "rgba(255,255,255,0.3)",
            }} />
          ))}
        </div>
      )}

      {/* Start Session button (pre-session overlay) */}
      {!sessionActive && !isStarting && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            zIndex: 20,
          }}
        >
          <button
            onClick={handleStartSession}
            style={{
              padding: "16px 40px",
              fontSize: "1.3rem",
              fontWeight: 600,
              color: "#fff",
              background: "rgba(100, 140, 255, 0.8)",
              border: "none",
              borderRadius: 12,
              cursor: "pointer",
              backdropFilter: "blur(10px)",
              boxShadow: "0 4px 20px rgba(100, 140, 255, 0.4)",
            }}
          >
            Start Session
          </button>
        </div>
      )}

      {/* Starting indicator */}
      {isStarting && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            color: "#fff",
            fontSize: "1.5rem",
            zIndex: 20,
          }}
        >
          Starting...
        </div>
      )}

      {/* Avatar PiP (top-right, session only) */}
      {sessionActive && (
        <AvatarPiP videoRef={avatar.avatarRef} isReady={avatar.isReady} />
      )}

      {/* Gesture visual feedback */}
      <GestureIndicator key={gestureKey} gesture={lastGesture} />

      {/* Product carousel (bottom, when products exist) */}
      {sessionActive && products.length > 0 && (
        <ProductCarousel items={products} onGesture={handleProductGesture} />
      )}

      {/* Voice indicator (bottom-left, session only) */}
      {sessionActive && (
        <VoiceIndicator
          isListening={stt.isListening}
          interimTranscript={stt.interimTranscript}
        />
      )}

      {/* Error indicators */}
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

