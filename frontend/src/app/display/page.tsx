"use client";

import { useState, useCallback, useRef } from "react";
import JennyVideoLayer from "@/components/display/JennyVideoLayer";
import MiraPanel, { MiraPanelHandle } from "@/components/display/MiraPanel";
import SubtitlesPanel, {
  SubtitleLine,
} from "@/components/display/SubtitlesPanel";
import MicButton from "@/components/display/MicButton";
import { useVoiceInput } from "@/hooks/useVoiceInput";
import styles from "@/components/display/display.module.css";

let lineId = 0;
function nextId(): string {
  return `line-${++lineId}`;
}

/** Stub responses for testing. Replace with backend integration. */
const STUB_RESPONSES = [
  "I love that look on you!",
  "Have you tried pairing that with a denim jacket?",
  "That color really complements your skin tone.",
  "Let me find some outfit options for you...",
  "Looking great! Want to try something bolder?",
];

export default function DisplayPage() {
  const [lines, setLines] = useState<SubtitleLine[]>([]);
  const miraRef = useRef<MiraPanelHandle>(null);

  const addLine = useCallback(
    (speaker: SubtitleLine["speaker"], text: string) => {
      setLines((prev) => [
        ...prev,
        { id: nextId(), speaker, text, timestamp: Date.now() },
      ]);
    },
    []
  );

  /**
   * Stub handler for user utterances.
   * TODO: Send to backend via Socket.io and receive Mira's response.
   */
  const handleUserUtterance = useCallback(
    (text: string) => {
      console.log("[Display] User said:", text);
      addLine("User", text);

      // Simulate Mira response after a short delay
      setTimeout(() => {
        const response =
          STUB_RESPONSES[Math.floor(Math.random() * STUB_RESPONSES.length)];
        addLine("Mira", response);
        miraRef.current?.speak(response);
      }, 800);
    },
    [addLine]
  );

  const { isListening, isSupported, error, toggle } = useVoiceInput({
    onResult: handleUserUtterance,
  });

  return (
    <main className={styles.displayRoot}>
      {/* Base layer: Jenny live video */}
      <JennyVideoLayer />

      {/* Overlays */}
      <div className={styles.overlays}>
        {/* Top row: subtitles left, Mira right */}
        <div className={styles.topRow}>
          <SubtitlesPanel lines={lines} />
          <MiraPanel ref={miraRef} />
        </div>

        {/* Spacer pushes mic to bottom */}
        <div className={styles.spacer} />
      </div>

      {/* Mic button (outside overlay flex for absolute positioning) */}
      <MicButton
        isListening={isListening}
        isSupported={isSupported}
        error={error}
        onToggle={toggle}
      />
    </main>
  );
}
