"use client";

interface IdleScreenProps {
  qrUrl: string;
}

export function IdleScreen({ qrUrl }: IdleScreenProps) {
  // Use Google Charts QR API (no npm dependency)
  const qrImageUrl = `https://chart.googleapis.com/chart?cht=qr&chs=300x300&chl=${encodeURIComponent(qrUrl)}&choe=UTF-8`;

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
      <img
        src={qrImageUrl}
        alt="Scan to start"
        width={300}
        height={300}
        style={{
          borderRadius: 16,
          border: "2px solid rgba(255,255,255,0.1)",
        }}
      />
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
