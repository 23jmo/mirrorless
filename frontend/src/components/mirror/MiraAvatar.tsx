"use client";

import { useState, useEffect, useRef } from "react";

export interface OccupiedRegion {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface MiraAvatarProps {
  occupiedRegions: OccupiedRegion[];
  screenWidth: number;
  screenHeight: number;
  avatarSize?: number;
  children?: React.ReactNode; // HeyGen video stream goes here
}

const AVATAR_SIZE = 250;
const REPOSITION_INTERVAL_MS = 3000;
const TRANSITION_MS = 1500;

// Candidate positions: corners and edge midpoints
function getCandidatePositions(
  sw: number,
  sh: number,
  aw: number,
  ah: number
) {
  const margin = 30;
  return [
    { x: sw - aw - margin, y: sh - ah - margin }, // bottom-right
    { x: margin, y: sh - ah - margin },             // bottom-left
    { x: sw - aw - margin, y: margin },             // top-right
    { x: margin, y: margin },                        // top-left
    { x: sw - aw - margin, y: (sh - ah) / 2 },     // middle-right
    { x: margin, y: (sh - ah) / 2 },                // middle-left
    { x: (sw - aw) / 2, y: margin },                // top-center
    { x: (sw - aw) / 2, y: sh - ah - margin },     // bottom-center
  ];
}

function rectsOverlap(
  ax: number, ay: number, aw: number, ah: number,
  bx: number, by: number, bw: number, bh: number
): boolean {
  return ax < bx + bw && ax + aw > bx && ay < by + bh && ay + ah > by;
}

export function findUnoccupiedPosition(
  occupied: OccupiedRegion[],
  screenWidth: number,
  screenHeight: number,
  avatarWidth: number,
  avatarHeight: number
): { x: number; y: number } {
  const candidates = getCandidatePositions(
    screenWidth, screenHeight, avatarWidth, avatarHeight
  );

  for (const candidate of candidates) {
    const hasOverlap = occupied.some((r) =>
      rectsOverlap(
        candidate.x, candidate.y, avatarWidth, avatarHeight,
        r.x, r.y, r.width, r.height
      )
    );
    if (!hasOverlap) return candidate;
  }

  // Fallback: bottom-right corner
  return candidates[0];
}

export function MiraAvatar({
  occupiedRegions,
  screenWidth,
  screenHeight,
  avatarSize = AVATAR_SIZE,
  children,
}: MiraAvatarProps) {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const initialized = useRef(false);

  // Initial position
  useEffect(() => {
    if (!initialized.current && screenWidth > 0) {
      const pos = findUnoccupiedPosition(
        occupiedRegions, screenWidth, screenHeight, avatarSize, avatarSize
      );
      setPosition(pos);
      initialized.current = true;
    }
  }, [screenWidth, screenHeight, avatarSize, occupiedRegions]);

  // Reposition periodically when overlays change
  useEffect(() => {
    const interval = setInterval(() => {
      const pos = findUnoccupiedPosition(
        occupiedRegions, screenWidth, screenHeight, avatarSize, avatarSize
      );
      setPosition(pos);
    }, REPOSITION_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [occupiedRegions, screenWidth, screenHeight, avatarSize]);

  return (
    <div
      style={{
        position: "absolute",
        left: position.x,
        top: position.y,
        width: avatarSize,
        height: avatarSize,
        borderRadius: "50%",
        overflow: "hidden",
        // Glassmorphism
        background: "rgba(255, 255, 255, 0.08)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        border: "1px solid rgba(255, 255, 255, 0.15)",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3), inset 0 0 20px rgba(255,255,255,0.05)",
        transition: `left ${TRANSITION_MS}ms ease-in-out, top ${TRANSITION_MS}ms ease-in-out`,
        zIndex: 25,
        pointerEvents: "none",
      }}
    >
      {children || (
        <div
          style={{
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "rgba(255,255,255,0.4)",
            fontSize: "0.8rem",
          }}
        >
          Mira
        </div>
      )}
    </div>
  );
}
