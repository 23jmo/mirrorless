"use client";

import { useState, useEffect } from "react";
import type { OutfitRecommendation } from "@/types/outfit";

interface OutfitInfoPanelProps {
  outfit: OutfitRecommendation | null;
  visible: boolean;
}

const DISPLAY_DURATION_MS = 5000;

export function OutfitInfoPanel({ outfit, visible }: OutfitInfoPanelProps) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!visible) {
      setShow(false);
      return;
    }
    setShow(true);
    const timer = setTimeout(() => setShow(false), DISPLAY_DURATION_MS);
    return () => clearTimeout(timer);
  }, [visible]);

  if (!show || !outfit) return null;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 40,
        right: 40,
        maxWidth: 350,
        padding: "20px 24px",
        background: "rgba(0, 0, 0, 0.7)",
        backdropFilter: "blur(10px)",
        borderRadius: 16,
        border: "1px solid rgba(255,255,255,0.1)",
        color: "#fff",
        zIndex: 30,
        animation: "fadeIn 300ms ease-out",
      }}
    >
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
      {outfit.items.map((item) => (
        <div key={item.id} style={{ marginBottom: 12 }}>
          <div style={{ fontSize: "1rem", fontWeight: 600 }}>{item.name}</div>
          <div style={{ fontSize: "0.85rem", color: "rgba(255,255,255,0.6)" }}>
            {item.brand} &middot; ${item.price.toFixed(2)}
          </div>
        </div>
      ))}
      {outfit.explanation && (
        <div
          style={{
            fontSize: "0.8rem",
            color: "rgba(255,255,255,0.5)",
            marginTop: 8,
            fontStyle: "italic",
          }}
        >
          {outfit.explanation}
        </div>
      )}
    </div>
  );
}
