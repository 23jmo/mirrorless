"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { StreamingTTS } from "@/lib/streaming-tts";
import type { AgentState } from "@/components/ui/orb";

export type OrbState = "idle" | "listening" | "thinking" | "speaking";

// Extended emotions for Mira video avatar (13 total)
export type MiraEmotion =
  | "idle"
  | "thinking"
  | "talking"
  | "happy"
  | "excited"
  | "concerned"
  | "sassy"
  | "disappointed"
  | "surprised"
  | "proud"
  | "flirty"
  | "judgy"
  | "sympathetic"
  // Legacy aliases
  | "neutral"
  | "teasing";

// For Mira video avatar state
export type MiraAvatarState = "idle" | "speaking";

// Map emotions to orb colors (for backward compatibility)
const EMOTION_COLORS: Record<string, [string, string]> = {
  idle: ["#F0F0F5", "#E8E8EE"],
  neutral: ["#F5E6A0", "#E8D680"],
  thinking: ["#B8C4D4", "#9AABBD"],
  talking: ["#F5E6A0", "#E8D680"],
  happy: ["#FFE066", "#FFD633"],
  excited: ["#FF9F43", "#FF7F00"],
  concerned: ["#A8D5BA", "#8CC49F"],
  sassy: ["#FF6B9D", "#FF4081"],
  disappointed: ["#9DB4C0", "#7A9AAD"],
  surprised: ["#FFB6C1", "#FF91A4"],
  proud: ["#4A6FA5", "#3A5C8C"],
  flirty: ["#FFB7D5", "#FF8FC4"],
  judgy: ["#C9B8D4", "#A896BB"],
  sympathetic: ["#B5D8E8", "#8FC4D8"],
  teasing: ["#FFF3B0", "#FFE580"],
};

// Map legacy emotion names to new ones
function normalizeEmotion(emotion: MiraEmotion): MiraEmotion {
  if (emotion === "neutral") return "idle";
  if (emotion === "teasing") return "sassy";
  return emotion;
}

/** Map OrbState to the Orb component's agentState prop. */
function toAgentState(state: OrbState): AgentState {
  switch (state) {
    case "listening":
      return "listening";
    case "thinking":
      return "thinking";
    case "speaking":
      return "talking";
    default:
      return null;
  }
}

export interface UseOrbAvatarReturn {
  // Original orb interface
  orbState: OrbState;
  agentState: AgentState;
  colors: [string, string];
  colorsRef: React.RefObject<[string, string]>;
  outputVolumeRef: React.RefObject<number>;
  getOutputVolume: () => number;
  speak: (text: string, emotion?: MiraEmotion) => void;
  setOrbState: (state: OrbState) => void;
  stop: () => void;
  isSpeaking: boolean;
  startSession: () => void;
  stopSession: () => void;
  
  // NEW: Mira video avatar interface
  miraEmotion: MiraEmotion;
  miraState: MiraAvatarState;
  setMiraEmotion: (emotion: MiraEmotion) => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useOrbAvatar(): UseOrbAvatarReturn {
  const [orbState, setOrbStateInternal] = useState<OrbState>("idle");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [colors, setColors] = useState<[string, string]>(EMOTION_COLORS.idle);
  
  // NEW: Mira video avatar state
  const [miraEmotion, setMiraEmotionInternal] = useState<MiraEmotion>("idle");
  const [miraState, setMiraState] = useState<MiraAvatarState>("idle");

  const colorsRef = useRef<[string, string]>(EMOTION_COLORS.idle);
  const outputVolumeRef = useRef<number>(0);
  const ttsRef = useRef<StreamingTTS | null>(null);
  const rafIdRef = useRef<number>(0);

  // Volume polling loop — reads from TTS analyser, writes to ref for Orb
  const startVolumeLoop = useCallback(() => {
    const tick = () => {
      const tts = ttsRef.current;
      outputVolumeRef.current = tts ? tts.getOutputVolume() : 0;
      rafIdRef.current = requestAnimationFrame(tick);
    };
    rafIdRef.current = requestAnimationFrame(tick);
  }, []);

  const stopVolumeLoop = useCallback(() => {
    cancelAnimationFrame(rafIdRef.current);
    outputVolumeRef.current = 0;
  }, []);

  const setOrbState = useCallback((state: OrbState) => {
    setOrbStateInternal(state);
    // Sync mira state
    if (state === "thinking") {
      setMiraEmotionInternal("thinking");
      setMiraState("idle");
    }
  }, []);

  const setMiraEmotion = useCallback((emotion: MiraEmotion) => {
    setMiraEmotionInternal(normalizeEmotion(emotion));
  }, []);

  const updateColors = useCallback((emotion: MiraEmotion) => {
    const normalized = normalizeEmotion(emotion);
    const c = EMOTION_COLORS[normalized] ?? EMOTION_COLORS.idle;
    colorsRef.current = c;
    setColors(c);
    // Also update mira emotion
    setMiraEmotionInternal(normalized);
  }, []);

  const speak = useCallback(
    (text: string, emotion: MiraEmotion = "idle") => {
      if (!text.trim() || !ttsRef.current) return;

      const normalized = normalizeEmotion(emotion);
      updateColors(normalized);
      setIsSpeaking(true);
      setOrbStateInternal("speaking");
      
      // NEW: Set mira to speaking state with emotion
      setMiraEmotionInternal(normalized);
      setMiraState("speaking");

      console.log(`[OrbAvatar] Speaking (emotion=${normalized}):`, text.slice(0, 80));

      ttsRef.current
        .speak(
          text,
          () => {
            // onStart — audio playback has begun
            console.log("[OrbAvatar] Playback started");
          },
          () => {
            // onEnd — audio playback finished
            console.log("[OrbAvatar] Playback finished");
            setIsSpeaking(false);
            setOrbStateInternal("idle");
            updateColors("idle");
            
            // NEW: Return mira to idle
            setMiraState("idle");
            setTimeout(() => setMiraEmotionInternal("idle"), 500);
          },
        )
        .catch(() => {
          setIsSpeaking(false);
          setOrbStateInternal("idle");
          updateColors("idle");
          setMiraState("idle");
          setMiraEmotionInternal("idle");
        });
    },
    [updateColors],
  );

  const stop = useCallback(() => {
    ttsRef.current?.stop();
    setIsSpeaking(false);
    setOrbStateInternal("idle");
    updateColors("idle");
    setMiraState("idle");
    setMiraEmotionInternal("idle");
  }, [updateColors]);

  const startSession = useCallback(() => {
    if (ttsRef.current) return;
    const tts = new StreamingTTS(API_URL);
    ttsRef.current = tts;
    startVolumeLoop();
    console.log("[OrbAvatar] Session started");
  }, [startVolumeLoop]);

  const stopSession = useCallback(() => {
    stopVolumeLoop();
    ttsRef.current?.destroy();
    ttsRef.current = null;
    setIsSpeaking(false);
    setOrbStateInternal("idle");
    updateColors("idle");
    setMiraState("idle");
    setMiraEmotionInternal("idle");
    console.log("[OrbAvatar] Session stopped");
  }, [stopVolumeLoop, updateColors]);

  const getOutputVolume = useCallback(() => {
    return ttsRef.current?.getOutputVolume() ?? 0;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancelAnimationFrame(rafIdRef.current);
      ttsRef.current?.destroy();
      ttsRef.current = null;
    };
  }, []);

  return {
    // Original orb interface
    orbState,
    agentState: toAgentState(orbState),
    colors,
    colorsRef,
    outputVolumeRef,
    getOutputVolume,
    speak,
    setOrbState,
    stop,
    isSpeaking,
    startSession,
    stopSession,
    
    // NEW: Mira video avatar interface
    miraEmotion,
    miraState,
    setMiraEmotion,
  };
}
