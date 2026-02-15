"use client";

import { useState } from "react";
import { MiraVideoAvatar, type MiraEmotion, type MiraAvatarState } from "@/components/ui/mira-video-avatar";

const EMOTIONS: MiraEmotion[] = [
  "idle", "thinking", "talking", "happy", "excited", "concerned",
  "sassy", "disappointed", "surprised", "proud", "flirty", "judgy", "sympathetic",
];

export default function DemoPage() {
  const [emotion, setEmotion] = useState<MiraEmotion>("idle");
  const [state, setState] = useState<MiraAvatarState>("idle");
  const [size, setSize] = useState(300);

  return (
    <main style={{ minHeight: "100vh", background: "#111", color: "#fff", padding: 40, fontFamily: "system-ui" }}>
      <h1 style={{ marginBottom: 20 }}>Mira Video Avatar Demo</h1>
      <div style={{ display: "flex", gap: 40, flexWrap: "wrap" }}>
        <div>
          <MiraVideoAvatar emotion={emotion} state={state} size={size} />
          <p style={{ marginTop: 10, textAlign: "center", opacity: 0.7 }}>{emotion} / {state}</p>
        </div>
        <div style={{ flex: 1, minWidth: 300 }}>
          <div style={{ marginBottom: 24 }}>
            <h3 style={{ marginBottom: 10 }}>State</h3>
            <div style={{ display: "flex", gap: 10 }}>
              {(["idle", "speaking"] as const).map(s => (
                <button key={s} onClick={() => setState(s)} style={{ padding: "10px 20px", background: state === s ? "#4a6fa5" : "#333", border: "none", borderRadius: 8, color: "#fff", cursor: "pointer" }}>
                  {s === "idle" ? "Idle (no lip)" : "Speaking (lip sync)"}
                </button>
              ))}
            </div>
          </div>
          <div style={{ marginBottom: 24 }}>
            <h3 style={{ marginBottom: 10 }}>Emotion</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
              {EMOTIONS.map(e => (
                <button key={e} onClick={() => setEmotion(e)} style={{ padding: "8px 12px", background: emotion === e ? "#4a6fa5" : "#333", border: "none", borderRadius: 6, color: "#fff", cursor: "pointer", fontSize: 13 }}>
                  {e}
                </button>
              ))}
            </div>
          </div>
          <div style={{ marginBottom: 24 }}>
            <h3>Size: {size}px</h3>
            <input type="range" min={100} max={500} value={size} onChange={e => setSize(Number(e.target.value))} style={{ width: "100%" }} />
          </div>
          <button onClick={() => { let i = 0; const iv = setInterval(() => { setEmotion(EMOTIONS[i % EMOTIONS.length]); setState(i % 2 === 0 ? "idle" : "speaking"); i++; if (i >= EMOTIONS.length * 2) clearInterval(iv); }, 2000); }} style={{ padding: "10px 20px", background: "#2a5", border: "none", borderRadius: 8, color: "#fff", cursor: "pointer" }}>
            Cycle All Emotions
          </button>
        </div>
      </div>
      <h2 style={{ marginTop: 60, marginBottom: 20 }}>All Emotions Preview</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 20 }}>
        {EMOTIONS.map(e => (
          <div key={e} style={{ textAlign: "center" }}>
            <MiraVideoAvatar emotion={e} state="idle" size={120} />
            <p style={{ marginTop: 8, fontSize: 14, opacity: 0.8 }}>{e}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
