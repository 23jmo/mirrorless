"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useCamera } from "@/hooks/useCamera";
import { useGestureRecognizer } from "@/hooks/useGestureRecognizer";
import { useHeyGenAvatar } from "@/hooks/useHeyGenAvatar";
import { useDeepgramSTT } from "@/hooks/useDeepgramSTT";
import { GestureIndicator } from "@/components/mirror/GestureIndicator";
import AvatarPiP from "@/components/mirror/AvatarPiP";
import VoiceIndicator from "@/components/mirror/VoiceIndicator";
import ProductCarousel, {
  type ProductCard,
} from "@/components/mirror/ProductCarousel";
import { SentenceBuffer } from "@/lib/sentence-buffer";
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
  const userId = searchParams.get("user_id");
  const mirrorId = searchParams.get("mirror_id") ?? process.env.NEXT_PUBLIC_MIRROR_ID ?? "MIRROR-A1";
  const { videoRef, isReady: isCameraReady, error: cameraError } = useCamera();

  // Gesture state (existing)
  const [lastGesture, setLastGesture] = useState<GestureType | null>(null);
  const gestureKeyRef = useRef(0);
  const [gestureKey, setGestureKey] = useState(0);

  // Session state
  const [sessionActive, setSessionActive] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [products, setProducts] = useState<ProductCard[]>([]);

  // Mirror text overlay from Poke (via send_to_mirror)
  const [mirrorText, setMirrorText] = useState<string | null>(null);
  const mirrorTextTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Hooks for avatar + voice
  const avatar = useHeyGenAvatar();
  const stt = useDeepgramSTT();

  // Pending transcripts queue (held while Mira is speaking)
  const pendingTranscriptsRef = useRef<string[]>([]);

  // Sentence buffer: accumulates mira_speech chunks → calls avatar.speak per sentence
  const sentenceBufferRef = useRef<SentenceBuffer | null>(null);
  useEffect(() => {
    sentenceBufferRef.current = new SentenceBuffer((sentence) => {
      avatar.speak(sentence);
    });
  }, [avatar.speak]);

  // --------------- Socket connection ---------------

  useEffect(() => {
    socket.connect();

    // Join mirror room (for Poke-driven events via MCP bridge)
    socket.emit("join_room", {
      mirror_id: mirrorId,
      ...(userId ? { user_id: userId } : {}),
    });

    return () => {
      socket.disconnect();
    };
  }, [userId, mirrorId]);

  // --------------- Snapshot handler (existing) ---------------

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

  // --------------- Mira speech streaming ---------------

  useEffect(() => {
    const handleMiraSpeech = (data: { text: string; is_chunk: boolean }) => {
      if (data.is_chunk) {
        sentenceBufferRef.current?.feed(data.text);
      } else {
        // End of stream — flush any remaining buffered text
        sentenceBufferRef.current?.flush();
      }
    };

    socket.on("mira_speech", handleMiraSpeech);
    return () => {
      socket.off("mira_speech", handleMiraSpeech);
    };
  }, []);

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
      mirrorTextTimeoutRef.current = setTimeout(() => setMirrorText(null), 15000);

      // Speak via TTS (uses the existing avatar or browser speech synthesis)
      if (avatar.isReady) {
        avatar.speak(data.text);
      } else if ("speechSynthesis" in window) {
        const utterance = new SpeechSynthesisUtterance(data.text);
        speechSynthesis.speak(utterance);
      }
    };

    socket.on("mirror_text", handleMirrorText);
    return () => {
      socket.off("mirror_text", handleMirrorText);
      if (mirrorTextTimeoutRef.current) {
        clearTimeout(mirrorTextTimeoutRef.current);
      }
    };
  }, [avatar.isReady, avatar.speak]);

  // --------------- Session lifecycle ---------------

  useEffect(() => {
    const handleSessionStarted = () => {
      setSessionActive(true);
      setIsStarting(false);
      avatar.startAvatar();
      stt.startListening();
    };

    const handleSessionEnded = () => {
      setSessionActive(false);
      setIsStarting(false);
      setProducts([]);
      avatar.clearQueue();
      avatar.stopAvatar();
      stt.stopListening();
    };

    const handleSessionError = () => {
      setIsStarting(false);
    };

    socket.on("session_active", handleSessionStarted);
    socket.on("session_ended", handleSessionEnded);
    socket.on("session_error", handleSessionError);

    return () => {
      socket.off("session_active", handleSessionStarted);
      socket.off("session_ended", handleSessionEnded);
      socket.off("session_error", handleSessionError);
    };
  }, [avatar.startAvatar, avatar.stopAvatar, avatar.clearQueue, stt.startListening, stt.stopListening]);

  // Fallback: auto-detect session start from first mira_speech if session_active isn't emitted
  const sessionStartedViaFallback = useRef(false);
  useEffect(() => {
    const handleFirstSpeech = () => {
      if (!sessionActive && !sessionStartedViaFallback.current) {
        sessionStartedViaFallback.current = true;
        setSessionActive(true);
        setIsStarting(false);
        avatar.startAvatar();
        stt.startListening();
      }
    };

    socket.on("mira_speech", handleFirstSpeech);
    return () => {
      socket.off("mira_speech", handleFirstSpeech);
      sessionStartedViaFallback.current = false;
    };
  }, [sessionActive, avatar.startAvatar, stt.startListening]);

  // --------------- Voice transcript → backend ---------------

  // When a final transcript arrives from Deepgram, either queue or send
  const lastTranscriptRef = useRef("");
  useEffect(() => {
    if (!stt.transcript || stt.transcript === lastTranscriptRef.current) return;
    lastTranscriptRef.current = stt.transcript;

    if (avatar.isSpeaking) {
      // Queue while Mira is speaking
      pendingTranscriptsRef.current.push(stt.transcript);
    } else {
      // Send immediately
      socket.emit("mirror_event", {
        user_id: userId,
        event: { type: "voice", transcript: stt.transcript },
      });
    }
  }, [stt.transcript, avatar.isSpeaking, userId]);

  // Flush pending transcripts when avatar stops speaking
  useEffect(() => {
    if (!avatar.isSpeaking && pendingTranscriptsRef.current.length > 0) {
      const combined = pendingTranscriptsRef.current.join(" ");
      pendingTranscriptsRef.current = [];
      socket.emit("mirror_event", {
        user_id: userId,
        event: { type: "voice", transcript: combined },
      });
    }
  }, [avatar.isSpeaking, userId]);

  // --------------- Start session from mirror ---------------

  const startSession = useCallback(() => {
    if (!userId || isStarting || sessionActive) return;
    setIsStarting(true);
    socket.emit("start_session", { user_id: userId });
  }, [userId, isStarting, sessionActive]);

  // --------------- Gesture handling (dual routing) ---------------

  const handleGesture = useCallback(
    (gesture: DetectedGesture) => {
      console.log("[Mirror] Gesture detected:", gesture.type, gesture.confidence);

      setLastGesture(gesture.type);
      gestureKeyRef.current += 1;
      setGestureKey(gestureKeyRef.current);

      // Frontend: animate carousel card immediately
      if (products.length > 0) {
        const carouselGesture = (
          window as unknown as Record<string, unknown>
        ).__carouselGesture as ((g: GestureType) => void) | undefined;
        carouselGesture?.(gesture.type);
      }

      // Backend: emit gesture event (async, Mira reacts verbally)
      socket.emit("mirror_event", {
        user_id: userId,
        event: {
          type: "gesture",
          gesture: gesture.type,
          confidence: gesture.confidence,
        },
      });
    },
    [userId, products.length],
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

      {/* Start Session button (pre-session) */}
      {!sessionActive && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 35,
            pointerEvents: "none",
          }}
        >
          {userId ? (
            <button
              onClick={startSession}
              disabled={isStarting}
              style={{
                pointerEvents: "auto",
                padding: "16px 40px",
                fontSize: "1.25rem",
                fontWeight: 600,
                color: "#fff",
                background: isStarting
                  ? "rgba(255, 255, 255, 0.1)"
                  : "rgba(255, 255, 255, 0.2)",
                border: "1px solid rgba(255, 255, 255, 0.3)",
                borderRadius: 12,
                cursor: isStarting ? "default" : "pointer",
                backdropFilter: "blur(8px)",
                transition: "background 0.2s",
              }}
            >
              {isStarting ? "Starting\u2026" : "Start Session"}
            </button>
          ) : (
            <div
              style={{
                pointerEvents: "auto",
                padding: "16px 24px",
                color: "rgba(255, 255, 255, 0.7)",
                background: "rgba(0, 0, 0, 0.5)",
                borderRadius: 12,
                fontSize: "1rem",
                textAlign: "center",
                backdropFilter: "blur(8px)",
              }}
            >
              No user — scan QR or add <code>?user_id=</code> to URL
            </div>
          )}
        </div>
      )}

      {/* HeyGen Avatar PiP (top-right) */}
      {sessionActive && (
        <AvatarPiP videoRef={avatar.videoRef} isReady={avatar.isReady} />
      )}

      {/* Gesture visual feedback */}
      <GestureIndicator key={gestureKey} gesture={lastGesture} />

      {/* Product carousel (bottom) */}
      <ProductCarousel
        items={products}
        onGesture={(gesture, item) => {
          console.log("[Mirror] Carousel gesture:", gesture, item.title);
        }}
      />

      {/* Voice indicator (bottom-left) */}
      {sessionActive && (
        <VoiceIndicator
          isListening={stt.isListening}
          interimTranscript={stt.interimTranscript}
        />
      )}

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
