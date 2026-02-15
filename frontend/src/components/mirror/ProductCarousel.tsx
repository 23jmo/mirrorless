"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { GestureType } from "@/types/gestures";

export interface ProductCard {
  product_id?: string;
  title: string;
  price?: string;
  image_url?: string;
  source?: string;
  link?: string;
}

interface ProductCarouselProps {
  items: ProductCard[];
  onGesture: (gesture: GestureType, item: ProductCard) => void;
}

export default function ProductCarousel({ items, onGesture }: ProductCarouselProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleGesture = useCallback(
    (gesture: GestureType) => {
      if (gesture === "swipe_left") {
        setActiveIndex((i) => Math.min(i + 1, items.length - 1));
      } else if (gesture === "swipe_right") {
        setActiveIndex((i) => Math.max(i - 1, 0));
      } else {
        const item = items[activeIndex];
        if (item) onGesture(gesture, item);
      }
    },
    [items, activeIndex, onGesture],
  );

  useEffect(() => {
    (window as unknown as Record<string, unknown>).__carouselGesture = handleGesture;
    return () => {
      delete (window as unknown as Record<string, unknown>).__carouselGesture;
    };
  }, [handleGesture]);

  return (
    <div
      ref={containerRef}
      style={{
        position: "absolute",
        bottom: 60,
        left: 0,
        right: 0,
        display: "flex",
        gap: 12,
        padding: "0 24px",
        overflowX: "auto",
        zIndex: 15,
        scrollbarWidth: "none",
      }}
    >
      {items.map((item, i) => (
        <div
          key={item.product_id ?? i}
          style={{
            flex: "0 0 180px",
            background: i === activeIndex ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.5)",
            borderRadius: 12,
            padding: 12,
            color: "#fff",
            backdropFilter: "blur(8px)",
            border: i === activeIndex ? "1px solid rgba(255,255,255,0.4)" : "1px solid transparent",
            transition: "all 0.2s ease",
          }}
        >
          {item.image_url && (
            <img
              src={item.image_url}
              alt={item.title}
              style={{ width: "100%", height: 120, objectFit: "cover", borderRadius: 8 }}
            />
          )}
          <div style={{ marginTop: 8, fontSize: "0.85rem", fontWeight: 500 }}>
            {item.title}
          </div>
          {item.price && (
            <div style={{ marginTop: 4, fontSize: "0.8rem", opacity: 0.7 }}>
              {item.price}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
