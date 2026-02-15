"use client";

import styles from "./display.module.css";

interface MicButtonProps {
  isListening: boolean;
  isSupported: boolean;
  error: string | null;
  onToggle: () => void;
}

export default function MicButton({
  isListening,
  isSupported,
  error,
  onToggle,
}: MicButtonProps) {
  return (
    <div className={styles.micContainer}>
      <button
        className={`${styles.glassPanel} ${styles.micButton} ${isListening ? styles.micActive : ""}`}
        onClick={onToggle}
        disabled={!isSupported}
        aria-label={isListening ? "Stop listening" : "Start listening"}
        aria-pressed={isListening}
        title={
          !isSupported
            ? "Speech recognition not supported in this browser"
            : undefined
        }
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={styles.micIcon}
          aria-hidden="true"
        >
          <rect x="9" y="2" width="6" height="12" rx="3" />
          <path d="M5 10a7 7 0 0 0 14 0" />
          <line x1="12" y1="17" x2="12" y2="22" />
          <line x1="8" y1="22" x2="16" y2="22" />
        </svg>
      </button>
      <span
        className={`${styles.micLabel} ${isListening ? styles.micLabelVisible : ""}`}
      >
        Listening...
      </span>
      {error && <span className={styles.micError}>{error}</span>}
      {!isSupported && (
        <span className={styles.micError}>Mic not supported</span>
      )}
    </div>
  );
}
