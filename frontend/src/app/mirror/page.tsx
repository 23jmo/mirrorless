"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useCamera } from "@/hooks/useCamera";
import { useGestureRecognizer } from "@/hooks/useGestureRecognizer";
import { useVoiceChat } from "@/hooks/useVoiceChat";
import { GestureIndicator } from "@/components/mirror/GestureIndicator";
import { FloatingMemoji } from "@/components/mirror/FloatingMemoji";
import { generateAvatar } from "@/lib/avatar-api";
import { generateSpeech } from "@/lib/avatar-api";
import { playAudioWithAnalysis } from "@/lib/audio-analysis";
import { socket } from "@/lib/socket";
import type { DetectedGesture, GestureType } from "@/types/gestures";

// Placeholder Memoji SVG (purple circle face) used before generation
const PLACEHOLDER_MEMOJI =
  "data:image/svg+xml," +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
      <defs>
        <radialGradient id="g" cx="50%" cy="40%" r="50%">
          <stop offset="0%" stop-color="#c084fc"/>
          <stop offset="100%" stop-color="#7c3aed"/>
        </radialGradient>
      </defs>
      <circle cx="100" cy="100" r="90" fill="url(#g)"/>
      <ellipse cx="72" cy="85" rx="8" ry="10" fill="#fff"/>
      <ellipse cx="128" cy="85" rx="8" ry="10" fill="#fff"/>
      <ellipse cx="72" cy="87" rx="4" ry="5" fill="#1e1b4b"/>
      <ellipse cx="128" cy="87" rx="4" ry="5" fill="#1e1b4b"/>
      <path d="M 78 125 Q 100 145 122 125" stroke="#fff" stroke-width="4" fill="none" stroke-linecap="round"/>
    </svg>`
  );

export default function MirrorPage() {
  const { videoRef, isReady: isCameraReady, error: cameraError } = useCamera();
  const [lastGesture, setLastGesture] = useState<GestureType | null>(null);
  const gestureKeyRef = useRef(0);
  const [gestureKey, setGestureKey] = useState(0);

  const [memojiSrc, setMemojiSrc] = useState(PLACEHOLDER_MEMOJI);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [amplitude, setAmplitude] = useState(0);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // Placeholder user ID for voice chat (in production, comes from auth)
  const [userId] = useState(() => crypto.randomUUID());

  // Voice chat hook
  const voiceChat = useVoiceChat({
    userId,
    onAmplitude: (a) => setAmplitude(a),
  });

  // Connect socket on mount, join user room
  useEffect(() => {
    socket.connect();
    socket.emit("join_room", { user_id: userId });
    return () => {
      socket.disconnect();
    };
  }, [userId]);

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

  // Capture webcam frame as base64
  const captureFrame = useCallback((): string | null => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) return null;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.8).split(",")[1]; // strip data URI prefix
  }, [videoRef]);

  // Generate Memoji avatar from webcam
  const handleGenerate = useCallback(async () => {
    setIsGenerating(true);
    setStatusMsg("Generating your Memoji...");
    try {
      const frame = captureFrame();
      const result = await generateAvatar(
        "Transform the person in this image into a high-quality 3D emoji avatar, Apple Memoji-style. Use a soft, rounded, cartoony aesthetic with smooth shading and clean lines. The avatar must precisely mimic the facial features, hairstyle, accessories and skin tone from the photo. Maintain a friendly, expressive facial expression. Output the result on a solid, clean, plain white background, rendered as a full-body or bust-shot, appearing as a professional 3D looking avatar on a black background",
        frame ?? undefined
      );
      setMemojiSrc(`data:${result.mimeType};base64,${result.imageBase64}`);
      setStatusMsg(null);

      // Mira greets after avatar is generated
      handleSpeak("Looking great! I've created your Memoji avatar. Swipe to browse outfits!");
    } catch (err) {
      console.error("Avatar generation failed:", err);
      setStatusMsg("Avatar generation failed — using placeholder");
      setTimeout(() => setStatusMsg(null), 3000);
    } finally {
      setIsGenerating(false);
    }
  }, [captureFrame]);

  // Auto-generate Memoji once camera is ready
  const hasGeneratedRef = useRef(false);
  useEffect(() => {
    if (isCameraReady && !hasGeneratedRef.current) {
      hasGeneratedRef.current = true;
      // Small delay to ensure a good webcam frame is available
      const timer = setTimeout(() => handleGenerate(), 1500);
      return () => clearTimeout(timer);
    }
  }, [isCameraReady, handleGenerate]);

  // TTS with lipsync amplitude
  const handleSpeak = useCallback(async (text: string) => {
    if (isSpeaking) return;
    setIsSpeaking(true);
    try {
      const audioBuffer = await generateSpeech(text);
      await playAudioWithAnalysis(audioBuffer, (a) => setAmplitude(a));
    } catch (err) {
      console.error("TTS failed:", err);
    } finally {
      setIsSpeaking(false);
      setAmplitude(0);
    }
  }, [isSpeaking]);

  // Combine speaking state from manual TTS and voice chat
  const anySpeaking = isSpeaking || voiceChat.isSpeaking;

  // Memoji scale pulse based on speech amplitude
  const memojiScale = 1 + amplitude * 0.15;

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
      {/* Pulse animation for mic button */}
      <style>{`
        @keyframes pulse-mic {
          0%, 100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.5); }
          50% { box-shadow: 0 0 0 12px rgba(34, 197, 94, 0); }
        }
      `}</style>

      {/* Webcam feed (mirrored, horizontal) */}
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

      {/* Dark overlay for mirror effect */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "linear-gradient(135deg, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.3) 50%, rgba(0,0,0,0.5) 100%)",
          zIndex: 5,
        }}
      />

      {/* Clock + date (top-left, mirror style) */}
      <MirrorClock />

      {/* Floating Memoji */}
      <div style={{ transform: `scale(${memojiScale})`, transformOrigin: "center center" }}>
        <FloatingMemoji src={memojiSrc} size={180} />
      </div>

      {/* Mic toggle (bottom center) */}
      <div
        style={{
          position: "absolute",
          bottom: 40,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 30,
        }}
      >
        <button
          onClick={() => voiceChat.isListening ? voiceChat.stop() : voiceChat.start()}
          style={{
            width: 56,
            height: 56,
            borderRadius: "50%",
            border: "1px solid rgba(255,255,255,0.3)",
            background: voiceChat.isListening
              ? voiceChat.isSpeaking
                ? "linear-gradient(135deg, #7c3aed, #a855f7)"
                : "linear-gradient(135deg, #16a34a, #22c55e)"
              : "rgba(255,255,255,0.15)",
            color: "#fff",
            fontSize: "1.4rem",
            cursor: "pointer",
            backdropFilter: "blur(10px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            animation: voiceChat.isListening && !voiceChat.isSpeaking ? "pulse-mic 2s ease-in-out infinite" : "none",
          }}
          title={voiceChat.isListening ? "Stop listening" : "Start voice chat"}
        >
          {voiceChat.isListening ? "\u{1F3A4}" : "\u{1F399}"}
        </button>
      </div>

      {/* Voice transcript overlay */}
      {voiceChat.isListening && voiceChat.transcript && (
        <div
          style={{
            position: "absolute",
            bottom: 110,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 30,
            maxWidth: "70%",
            padding: "10px 20px",
            borderRadius: 20,
            background: "rgba(0,0,0,0.6)",
            backdropFilter: "blur(10px)",
            color: "rgba(255,255,255,0.9)",
            fontSize: "1rem",
            fontWeight: 400,
            textAlign: "center",
          }}
        >
          {voiceChat.transcript}
        </div>
      )}

      {/* Mira response overlay */}
      {voiceChat.miraText && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            right: 30,
            transform: "translateY(-50%)",
            zIndex: 30,
            maxWidth: 320,
            padding: "16px 20px",
            borderRadius: 16,
            background: "rgba(124, 58, 237, 0.25)",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(168, 85, 247, 0.4)",
            color: "#fff",
            fontSize: "0.95rem",
            fontWeight: 400,
            lineHeight: 1.5,
          }}
        >
          <div style={{ fontSize: "0.75rem", fontWeight: 600, opacity: 0.7, marginBottom: 6 }}>
            Mira
          </div>
          {voiceChat.miraText}
        </div>
      )}

      {/* Status message */}
      {statusMsg && (
        <div
          style={{
            position: "absolute",
            top: 30,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 30,
            padding: "10px 24px",
            borderRadius: 30,
            background: "rgba(0,0,0,0.6)",
            backdropFilter: "blur(10px)",
            color: "#fff",
            fontSize: "0.95rem",
            fontWeight: 500,
          }}
        >
          {statusMsg}
        </div>
      )}

      {/* Gesture visual feedback */}
      <GestureIndicator key={gestureKey} gesture={lastGesture} />

      {/* Error indicators */}
      {(cameraError || modelError) && (
        <div
          style={{
            position: "absolute",
            bottom: 100,
            left: 20,
            color: "#f44",
            fontSize: "0.9rem",
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

/** Simple clock widget for the mirror UI */
function MirrorClock() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const timeStr = time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const dateStr = time.toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" });

  return (
    <div
      style={{
        position: "absolute",
        top: 30,
        left: 30,
        zIndex: 10,
        color: "rgba(255,255,255,0.85)",
      }}
    >
      <div style={{ fontSize: "3rem", fontWeight: 200, letterSpacing: "0.05em" }}>
        {timeStr}
      </div>
      <div style={{ fontSize: "1.1rem", fontWeight: 300, opacity: 0.7, marginTop: 4 }}>
        {dateStr}
      </div>
    </div>
  );
}
