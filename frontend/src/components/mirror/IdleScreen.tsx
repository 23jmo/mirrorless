"use client";

import { QRCodeSVG } from "qrcode.react";

interface IdleScreenProps {
  qrUrl: string;
}

export function IdleScreen({ qrUrl }: IdleScreenProps) {
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "#000",
        zIndex: 50,
      }}
    >
      <div
        style={{
          padding: 16,
          background: "#fff",
          borderRadius: 16,
          border: "2px solid rgba(255,255,255,0.1)",
        }}
      >
        <QRCodeSVG value={qrUrl} size={268} />
      </div>
      <div
        style={{
          marginTop: 24,
          color: "rgba(255,255,255,0.5)",
          fontSize: "1.2rem",
          fontWeight: 300,
          letterSpacing: "0.05em",
        }}
      >
        Scan to start your style session
      </div>
    </div>
  );
}
