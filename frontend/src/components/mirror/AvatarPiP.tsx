"use client";

import type { RefObject } from "react";

interface AvatarPiPProps {
  videoRef: RefObject<HTMLVideoElement | null>;
  isReady: boolean;
}

export default function AvatarPiP({ videoRef, isReady }: AvatarPiPProps) {
  return (
    <video
      ref={videoRef}
      autoPlay
      playsInline
      style={{
        position: "absolute",
        top: 20,
        right: 20,
        width: 240,
        height: 240,
        borderRadius: 16,
        objectFit: "cover",
        zIndex: 15,
        opacity: isReady ? 1 : 0,
        transition: "opacity 0.3s ease",
        pointerEvents: "none",
      }}
    />
  );
}
