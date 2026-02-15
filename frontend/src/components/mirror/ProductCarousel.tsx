"use client";

import type { GestureType } from "@/types/gestures";

export interface ProductCard {
  title: string;
  price: string;
  image_url: string;
  link: string;
  source: string;
  rating?: number;
  rating_count?: number;
}

interface ProductCarouselProps {
  items: ProductCard[];
  onGesture?: (gesture: GestureType, item: ProductCard) => void;
}

export default function ProductCarousel({ items }: ProductCarouselProps) {
  if (items.length === 0) return null;

  return (
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        width: "100%",
        zIndex: 30,
        padding: "16px 20px 24px",
        background:
          "linear-gradient(transparent, rgba(0, 0, 0, 0.85) 30%)",
      }}
    >
      <div
        style={{
          display: "flex",
          gap: 14,
          overflowX: "auto",
          paddingBottom: 4,
          scrollSnapType: "x mandatory",
        }}
      >
        {items.map((item, i) => (
          <a
            key={i}
            href={item.link}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              minWidth: 180,
              maxWidth: 200,
              flexShrink: 0,
              scrollSnapAlign: "start",
              background: "rgba(255, 255, 255, 0.1)",
              backdropFilter: "blur(12px)",
              border: "1px solid rgba(255, 255, 255, 0.15)",
              borderRadius: 12,
              padding: 12,
              textDecoration: "none",
              color: "#fff",
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}
          >
            {item.image_url && (
              <img
                src={item.image_url}
                alt={item.title}
                style={{
                  width: "100%",
                  height: 140,
                  objectFit: "contain",
                  borderRadius: 8,
                  background: "rgba(255, 255, 255, 0.9)",
                }}
              />
            )}
            <div
              style={{
                fontSize: "0.85rem",
                fontWeight: 600,
                lineHeight: 1.3,
                overflow: "hidden",
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
              }}
            >
              {item.title}
            </div>
            <div
              style={{
                fontSize: "0.95rem",
                fontWeight: 700,
                color: "#a78bfa",
              }}
            >
              {item.price}
            </div>
            <div
              style={{
                fontSize: "0.7rem",
                color: "rgba(255, 255, 255, 0.6)",
              }}
            >
              {item.source}
              {item.rating ? ` | ${item.rating}★` : ""}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
