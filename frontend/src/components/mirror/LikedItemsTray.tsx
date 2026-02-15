"use client";

export interface LikedOutfitThumbnail {
  imageUrl: string;
  outfitName: string;
}

interface LikedItemsTrayProps {
  items: LikedOutfitThumbnail[];
}

const MAX_VISIBLE = 5;
const THUMB_SIZE = 44;

export function LikedItemsTray({ items }: LikedItemsTrayProps) {
  if (items.length === 0) return null;

  const visible = items.slice(-MAX_VISIBLE);
  const overflow = items.length - MAX_VISIBLE;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 80,
        right: 24,
        zIndex: 12,
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 12px",
        background: "rgba(255, 255, 255, 0.08)",
        backdropFilter: "blur(10px)",
        WebkitBackdropFilter: "blur(10px)",
        borderRadius: 14,
        border: "1px solid rgba(255, 255, 255, 0.12)",
      }}
    >
      {/* Count badge */}
      <div
        style={{
          minWidth: 28,
          height: 28,
          borderRadius: 14,
          background: "rgba(100, 140, 255, 0.8)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#fff",
          fontSize: "0.75rem",
          fontWeight: 700,
          padding: "0 6px",
        }}
      >
        {items.length}
      </div>

      {/* Thumbnails */}
      {visible.map((item, i) => (
        <div
          key={`${item.outfitName}-${i}`}
          style={{
            width: THUMB_SIZE,
            height: THUMB_SIZE,
            borderRadius: 8,
            overflow: "hidden",
            border: "2px solid rgba(255, 255, 255, 0.2)",
            flexShrink: 0,
            animation: "slideInScale 400ms ease-out both",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={item.imageUrl}
            alt={item.outfitName}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
          />
        </div>
      ))}

      {/* Overflow indicator */}
      {overflow > 0 && (
        <div
          style={{
            color: "rgba(255, 255, 255, 0.5)",
            fontSize: "0.75rem",
            fontWeight: 600,
            whiteSpace: "nowrap",
          }}
        >
          +{overflow}
        </div>
      )}

      <style>{`
        @keyframes slideInScale {
          from {
            opacity: 0;
            transform: scale(0.5) translateX(20px);
          }
          to {
            opacity: 1;
            transform: scale(1) translateX(0);
          }
        }
      `}</style>
    </div>
  );
}
