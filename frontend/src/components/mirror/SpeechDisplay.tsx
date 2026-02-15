"use client";

interface SpeechDisplayProps {
  text: string;
  visible: boolean;
}

export function SpeechDisplay({ text, visible }: SpeechDisplayProps) {
  return (
    <div
      style={{
        position: "absolute",
        bottom: 120,
        left: "50%",
        transform: "translateX(-50%)",
        maxWidth: "70vw",
        fontSize: "1.3rem",
        lineHeight: 1.6,
        color: "#fff",
        textAlign: "center",
        textShadow: "0 1px 4px rgba(0,0,0,0.8)",
        pointerEvents: "none",
        zIndex: 10,
        opacity: visible ? 1 : 0,
        transition: "opacity 300ms ease",
      }}
    >
      {text}
    </div>
  );
}
