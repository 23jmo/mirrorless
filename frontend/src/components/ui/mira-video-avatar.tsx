"use client";

import { useEffect, useRef, useState } from "react";

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
  | "sympathetic";

export type MiraAvatarState = "idle" | "speaking";

interface MiraVideoAvatarProps {
  emotion?: MiraEmotion;
  state?: MiraAvatarState;
  className?: string;
  size?: number;
}

/**
 * Get the video path for a given emotion and state.
 * - When speaking: use the talking version with lip movement
 * - When idle: use the emotion loop (no lip movement)
 */
function getVideoPath(emotion: MiraEmotion, state: MiraAvatarState): string {
  const basePath = "/avatar/loops/seamless";
  
  if (state === "speaking") {
    // Use talking version with lip movement
    return `${basePath}/talking/${emotion}_talking.mp4`;
  } else {
    // Use emotion loop (no lip movement)
    return `${basePath}/${emotion}_loop.mp4`;
  }
}

export function MiraVideoAvatar({
  emotion = "idle",
  state = "idle",
  className,
  size = 200,
}: MiraVideoAvatarProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentSrc, setCurrentSrc] = useState<string>("");
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Update video source when emotion or state changes
  useEffect(() => {
    const newSrc = getVideoPath(emotion, state);
    
    if (newSrc !== currentSrc) {
      setIsTransitioning(true);
      
      // Small delay to allow fade out, then switch
      const timeout = setTimeout(() => {
        setCurrentSrc(newSrc);
        setIsTransitioning(false);
      }, 100);
      
      return () => clearTimeout(timeout);
    }
  }, [emotion, state, currentSrc]);

  // Auto-play when source changes
  useEffect(() => {
    if (videoRef.current && currentSrc) {
      videoRef.current.load();
      videoRef.current.play().catch((err) => {
        console.warn("[MiraVideoAvatar] Autoplay blocked:", err);
      });
    }
  }, [currentSrc]);

  return (
    <div
      className={className}
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        overflow: "hidden",
        background: "#000",
        position: "relative",
      }}
    >
      <video
        ref={videoRef}
        src={currentSrc}
        autoPlay
        loop
        muted
        playsInline
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity: isTransitioning ? 0.7 : 1,
          transition: "opacity 0.15s ease-in-out",
        }}
      />
    </div>
  );
}
