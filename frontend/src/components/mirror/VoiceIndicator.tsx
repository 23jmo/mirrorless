"use client";

interface VoiceIndicatorProps {
  isListening: boolean;
  interimTranscript: string;
}

export default function VoiceIndicator({ isListening, interimTranscript }: VoiceIndicatorProps) {
  if (!isListening && !interimTranscript) return null;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 24,
        left: 24,
        display: "flex",
        alignItems: "center",
        gap: 10,
        zIndex: 15,
        pointerEvents: "none",
      }}
    >
      {isListening && (
        <div
          style={{
            width: 12,
            height: 12,
            borderRadius: "50%",
            background: "#4caf50",
            boxShadow: "0 0 8px rgba(76, 175, 80, 0.6)",
          }}
        />
      )}
      {interimTranscript && (
        <span
          style={{
            color: "rgba(255, 255, 255, 0.7)",
            fontSize: "0.95rem",
            maxWidth: 400,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {interimTranscript}
        </span>
      )}
    </div>
  );
}
