"use client";

import { useEffect, useRef, useState } from "react";

interface FloatingMemojiProps {
  src: string; // data URI or URL
  size?: number;
}

/**
 * A Memoji avatar that floats around the screen with smooth drift + gentle bob.
 * Bounces off edges like a screensaver.
 */
export function FloatingMemoji({ src, size = 180 }: FloatingMemojiProps) {
  const posRef = useRef({ x: 0, y: 0 });
  const velRef = useRef({ vx: 0, vy: 0 });
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const rafRef = useRef<number>(0);
  const timeRef = useRef(0);

  useEffect(() => {
    // Start near center with random offset
    const startX = window.innerWidth / 2 - size / 2 + (Math.random() - 0.5) * 200;
    const startY = window.innerHeight / 2 - size / 2 + (Math.random() - 0.5) * 100;
    posRef.current = { x: startX, y: startY };

    // Random initial drift direction
    const angle = Math.random() * Math.PI * 2;
    const speed = 0.8 + Math.random() * 0.6;
    velRef.current = { vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed };

    let lastTime = performance.now();

    function animate(now: number) {
      const dt = Math.min((now - lastTime) / 16, 3); // normalize to ~60fps, cap
      lastTime = now;
      timeRef.current += dt * 0.02;

      const p = posRef.current;
      const v = velRef.current;

      // Move
      p.x += v.vx * dt;
      p.y += v.vy * dt;

      // Bounce off edges
      const maxX = window.innerWidth - size;
      const maxY = window.innerHeight - size;

      if (p.x <= 0) {
        p.x = 0;
        v.vx = Math.abs(v.vx);
      } else if (p.x >= maxX) {
        p.x = maxX;
        v.vx = -Math.abs(v.vx);
      }

      if (p.y <= 0) {
        p.y = 0;
        v.vy = Math.abs(v.vy);
      } else if (p.y >= maxY) {
        p.y = maxY;
        v.vy = -Math.abs(v.vy);
      }

      setPos({ x: p.x, y: p.y });
      rafRef.current = requestAnimationFrame(animate);
    }

    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [size]);

  // Gentle bob offset via sine
  const bob = Math.sin(timeRef.current) * 8;

  return (
    <div
      style={{
        position: "absolute",
        left: pos.x,
        top: pos.y + bob,
        width: size,
        height: size,
        zIndex: 20,
        pointerEvents: "none",
        transition: "filter 0.3s",
        filter: "drop-shadow(0 0 30px rgba(255,255,255,0.3))",
      }}
    >
      <img
        src={src}
        alt="Memoji Avatar"
        style={{
          width: "100%",
          height: "100%",
          objectFit: "contain",
          borderRadius: "50%",
        }}
        draggable={false}
      />
    </div>
  );
}
