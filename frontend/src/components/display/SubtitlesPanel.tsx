"use client";

import { useEffect, useRef } from "react";
import styles from "./display.module.css";

export interface SubtitleLine {
  id: string;
  speaker: "User" | "Mira" | "Jenny";
  text: string;
  timestamp: number;
}

interface SubtitlesPanelProps {
  lines: SubtitleLine[];
  maxVisible?: number;
}

export default function SubtitlesPanel({
  lines,
  maxVisible = 8,
}: SubtitlesPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const visible = lines.slice(-maxVisible);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines.length]);

  return (
    <div
      className={`${styles.glassPanel} ${styles.subtitlesPanel}`}
      aria-label="Conversation subtitles"
      aria-live="polite"
    >
      <div className={styles.subtitlesScroll} ref={scrollRef}>
        {visible.length === 0 && (
          <p className={styles.subtitlesEmpty}>Waiting for conversation...</p>
        )}
        {visible.map((line, i) => {
          const opacity = Math.max(
            0.3,
            (i + 1) / visible.length
          );
          return (
            <div
              key={line.id}
              className={styles.subtitleLine}
              style={{ opacity }}
            >
              <span
                className={styles.subtitleSpeaker}
                data-speaker={line.speaker}
              >
                {line.speaker}
              </span>
              <span className={styles.subtitleText}>{line.text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
