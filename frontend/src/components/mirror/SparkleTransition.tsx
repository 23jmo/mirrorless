"use client";

import { useState, useEffect } from "react";

interface SparkleTransitionProps {
  active: boolean;
  onComplete?: () => void;
}

const SPARKLE_COUNT = 20;
const DURATION_MS = 600;

interface Sparkle {
  id: number;
  x: number;
  y: number;
  size: number;
  delay: number;
}

function generateSparkles(): Sparkle[] {
  return Array.from({ length: SPARKLE_COUNT }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: 4 + Math.random() * 8,
    delay: Math.random() * 300,
  }));
}

export function SparkleTransition({ active, onComplete }: SparkleTransitionProps) {
  const [sparkles, setSparkles] = useState<Sparkle[]>([]);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!active) return;

    setSparkles(generateSparkles());
    setVisible(true);

    const timer = setTimeout(() => {
      setVisible(false);
      onComplete?.();
    }, DURATION_MS);

    return () => clearTimeout(timer);
  }, [active, onComplete]);

  if (!visible) return null;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        zIndex: 15,
        overflow: "hidden",
      }}
    >
      <style>{`
        @keyframes sparkle-pop {
          0% { transform: scale(0) rotate(0deg); opacity: 1; }
          50% { transform: scale(1) rotate(180deg); opacity: 1; }
          100% { transform: scale(0) rotate(360deg); opacity: 0; }
        }
      `}</style>
      {sparkles.map((s) => (
        <div
          key={s.id}
          style={{
            position: "absolute",
            left: `${s.x}%`,
            top: `${s.y}%`,
            width: s.size,
            height: s.size,
            background: "radial-gradient(circle, #fff 0%, #aef 40%, transparent 70%)",
            borderRadius: "50%",
            boxShadow: "0 0 6px 2px rgba(174,239,255,0.6)",
            animation: `sparkle-pop ${DURATION_MS}ms ease-out ${s.delay}ms both`,
          }}
        />
      ))}
    </div>
  );
}
