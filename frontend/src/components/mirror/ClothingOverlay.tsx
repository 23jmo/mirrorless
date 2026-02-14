"use client";

import { useRef, useEffect, useState } from "react";
import type { PoseResult } from "@/types/pose";
import type { OutfitRecommendation } from "@/types/outfit";
import { computeAffineTransform } from "@/lib/pose-overlay";

interface ClothingOverlayProps {
  pose: PoseResult | null;
  outfit: OutfitRecommendation | null;
  width: number;
  height: number;
}

export function ClothingOverlay({ pose, outfit, width, height }: ClothingOverlayProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const imagesRef = useRef<Map<string, HTMLImageElement>>(new Map());
  const [loadedImages, setLoadedImages] = useState<Set<string>>(new Set());

  // Preload clothing images when outfit changes
  useEffect(() => {
    if (!outfit) {
      imagesRef.current.clear();
      setLoadedImages(new Set());
      return;
    }

    const newImages = new Map<string, HTMLImageElement>();
    const loaded = new Set<string>();

    for (const item of outfit.items) {
      if (imagesRef.current.has(item.id)) {
        newImages.set(item.id, imagesRef.current.get(item.id)!);
        loaded.add(item.id);
        continue;
      }

      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        loaded.add(item.id);
        setLoadedImages(new Set(loaded));
      };
      img.src = item.image_url;
      newImages.set(item.id, img);
    }

    imagesRef.current = newImages;
    setLoadedImages(loaded);
  }, [outfit]);

  // Render overlay on each pose update
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !pose || !outfit) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);

    for (const item of outfit.items) {
      const img = imagesRef.current.get(item.id);
      if (!img || !loadedImages.has(item.id)) continue;

      const transform = computeAffineTransform(
        pose.landmarks,
        item.category,
        width,
        height
      );
      if (!transform) continue;

      ctx.save();
      ctx.translate(transform.x, transform.y);
      ctx.rotate(transform.rotation);
      ctx.drawImage(
        img,
        -transform.width / 2,
        -transform.height / 2,
        transform.width,
        transform.height
      );
      ctx.restore();
    }
  }, [pose, outfit, width, height, loadedImages]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        zIndex: 10,
      }}
    />
  );
}
