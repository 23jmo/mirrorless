"use client";

interface OutfitDotsProps {
  count: number;
  activeIndex: number;
}

export function OutfitDots({ count, activeIndex }: OutfitDotsProps) {
  if (count <= 1) return null;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 20,
        left: "50%",
        transform: "translateX(-50%)",
        display: "flex",
        gap: 8,
        zIndex: 18,
        pointerEvents: "none",
      }}
    >
      {Array.from({ length: count }, (_, i) => (
        <div
          key={i}
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: i === activeIndex ? "#fff" : "rgba(255,255,255,0.3)",
            transition: "background 200ms ease",
          }}
        />
      ))}
    </div>
  );
}
