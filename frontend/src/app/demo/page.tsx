"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { MiraVideoAvatar } from "@/components/ui/mira-video-avatar";
import { useOrbAvatar, type MiraEmotion, type MiraAvatarState } from "@/hooks/useOrbAvatar";

// Lazy load the Orb to avoid SSR issues
const Orb = dynamic(
  () => import("@/components/ui/orb").then((mod) => ({ default: mod.Orb })),
  { ssr: false }
);

const EMOTIONS: MiraEmotion[] = [
  "idle", "thinking", "talking", "happy", "excited", "concerned",
  "sassy", "disappointed", "surprised", "proud", "flirty", "judgy", "sympathetic",
];

export default function DemoPage() {
  const orb = useOrbAvatar();
  const [manualEmotion, setManualEmotion] = useState<MiraEmotion>("idle");
  const [manualState, setManualState] = useState<MiraAvatarState>("idle");
  const [size, setSize] = useState(200);
  const [useHook, setUseHook] = useState(false); // Toggle between manual and hook-driven

  // Use hook values or manual values
  const emotion = useHook ? orb.miraEmotion : manualEmotion;
  const state = useHook ? orb.miraState : manualState;

  const handleEmotionClick = (e: MiraEmotion) => {
    if (useHook) {
      orb.setMiraEmotion(e);
    } else {
      setManualEmotion(e);
    }
  };

  const handleStateClick = (s: MiraAvatarState) => {
    if (useHook) {
      // Can't directly set miraState via hook - it's controlled by speak()
      // But we can trigger a test speak
      if (s === "speaking") {
        orb.speak("Testing the avatar speech system!", manualEmotion);
      }
    } else {
      setManualState(s);
    }
  };

  return (
    <main style={{ minHeight: "100vh", background: "#111", color: "#fff", padding: 40, fontFamily: "system-ui" }}>
      <h1 style={{ marginBottom: 10 }}>Mira Avatar Demo</h1>
      <p style={{ opacity: 0.6, marginBottom: 30 }}>Integrated with useOrbAvatar hook - Orb and Mira Video Avatar side by side</p>

      {/* Mode toggle */}
      <div style={{ marginBottom: 30 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
          <input 
            type="checkbox" 
            checked={useHook} 
            onChange={(e) => setUseHook(e.target.checked)}
            style={{ width: 20, height: 20 }}
          />
          <span>Use Hook (synced with Orb) - requires backend for TTS</span>
        </label>
      </div>

      <div style={{ display: "flex", gap: 60, flexWrap: "wrap", marginBottom: 40 }}>
        {/* Orb Avatar */}
        <div style={{ textAlign: "center" }}>
          <h3 style={{ marginBottom: 15 }}>Orb Avatar</h3>
          <div style={{ width: size, height: size, borderRadius: "50%", overflow: "hidden" }}>
            <Orb
              className="h-full w-full"
              colorsRef={orb.colorsRef}
              agentState={orb.agentState}
              seed={42}
            />
          </div>
          <p style={{ marginTop: 10, opacity: 0.7, fontSize: 14 }}>
            state: {orb.orbState}
          </p>
        </div>

        {/* Mira Video Avatar */}
        <div style={{ textAlign: "center" }}>
          <h3 style={{ marginBottom: 15 }}>Mira Video Avatar</h3>
          <MiraVideoAvatar emotion={emotion} state={state} size={size} />
          <p style={{ marginTop: 10, opacity: 0.7, fontSize: 14 }}>
            {emotion} / {state}
          </p>
        </div>
      </div>

      {/* Controls */}
      <div style={{ maxWidth: 600 }}>
        {/* State Toggle */}
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 10 }}>Avatar State</h3>
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={() => handleStateClick("idle")}
              style={{
                padding: "10px 20px",
                background: state === "idle" ? "#4a6fa5" : "#333",
                border: "none",
                borderRadius: 8,
                color: "#fff",
                cursor: "pointer",
              }}
            >
              Idle (no lip sync)
            </button>
            <button
              onClick={() => handleStateClick("speaking")}
              style={{
                padding: "10px 20px",
                background: state === "speaking" ? "#4a6fa5" : "#333",
                border: "none",
                borderRadius: 8,
                color: "#fff",
                cursor: "pointer",
              }}
            >
              Speaking (lip sync)
            </button>
          </div>
        </div>

        {/* Emotion Grid */}
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 10 }}>Emotion</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
            {EMOTIONS.map((e) => (
              <button
                key={e}
                onClick={() => handleEmotionClick(e)}
                style={{
                  padding: "8px 12px",
                  background: emotion === e ? "#4a6fa5" : "#333",
                  border: "none",
                  borderRadius: 6,
                  color: "#fff",
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                {e}
              </button>
            ))}
          </div>
        </div>

        {/* Size Slider */}
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 10 }}>Size: {size}px</h3>
          <input
            type="range"
            min={100}
            max={400}
            value={size}
            onChange={(e) => setSize(Number(e.target.value))}
            style={{ width: "100%" }}
          />
        </div>

        {/* Auto-cycle demo */}
        <div>
          <button
            onClick={() => {
              let i = 0;
              const interval = setInterval(() => {
                const e = EMOTIONS[i % EMOTIONS.length];
                const s: MiraAvatarState = i % 2 === 0 ? "idle" : "speaking";
                setManualEmotion(e);
                setManualState(s);
                if (useHook) orb.setMiraEmotion(e);
                i++;
                if (i >= EMOTIONS.length * 2) clearInterval(interval);
              }, 1500);
            }}
            style={{
              padding: "12px 24px",
              background: "#2a5",
              border: "none",
              borderRadius: 8,
              color: "#fff",
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            ▶ Cycle All Emotions
          </button>
        </div>
      </div>

      {/* All emotions preview grid */}
      <h2 style={{ marginTop: 60, marginBottom: 20 }}>All Emotions Preview</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: 20 }}>
        {EMOTIONS.map((e) => (
          <div 
            key={e} 
            style={{ textAlign: "center", cursor: "pointer" }}
            onClick={() => handleEmotionClick(e)}
          >
            <MiraVideoAvatar emotion={e} state="idle" size={100} />
            <p style={{ marginTop: 8, fontSize: 12, opacity: 0.8 }}>{e}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
