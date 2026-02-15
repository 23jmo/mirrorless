"use client";

import { useRef, useEffect } from "react";
import styles from "./display.module.css";

interface JennyVideoLayerProps {
  /** Video source URL. If null, shows a placeholder. */
  src?: string | null;
  /** MediaStream to display instead of a URL source. */
  stream?: MediaStream | null;
}

/**
 * Primary video layer for Jenny's live feed.
 * Accepts either a URL src or a MediaStream.
 * TODO: Replace placeholder with actual Jenny live video source once available.
 */
export default function JennyVideoLayer({
  src = null,
  stream = null,
}: JennyVideoLayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (!videoRef.current) return;
    if (stream) {
      videoRef.current.srcObject = stream;
    } else if (src) {
      videoRef.current.srcObject = null;
      videoRef.current.src = src;
    }
  }, [src, stream]);

  const hasSource = src || stream;

  return (
    <div className={styles.jennyLayer}>
      {hasSource ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          loop={!!src}
          className={styles.jennyVideo}
        />
      ) : (
        <div className={styles.jennyPlaceholder}>
          <div className={styles.jennyPlaceholderPulse} />
        </div>
      )}
    </div>
  );
}
