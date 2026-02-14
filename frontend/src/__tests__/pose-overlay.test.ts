import { describe, it, expect } from "vitest";
import {
  getLandmarkPixelCoords,
  computeAffineTransform,
  getCategoryLandmarks,
} from "@/lib/pose-overlay";
import type { PoseLandmark } from "@/types/pose";

function makeLandmark(x: number, y: number, vis = 0.9): PoseLandmark {
  return { x, y, z: 0, visibility: vis };
}

describe("getLandmarkPixelCoords", () => {
  it("converts normalized coords to pixel coords", () => {
    const landmark = makeLandmark(0.5, 0.5);
    const result = getLandmarkPixelCoords(landmark, 1920, 1080);
    expect(result).toEqual({ x: 960, y: 540 });
  });

  it("handles edge coordinates", () => {
    const landmark = makeLandmark(0, 0);
    const result = getLandmarkPixelCoords(landmark, 1920, 1080);
    expect(result).toEqual({ x: 0, y: 0 });
  });
});

describe("getCategoryLandmarks", () => {
  it("returns shoulder and hip indices for tops", () => {
    const result = getCategoryLandmarks("tops");
    expect(result).toEqual({
      topLeft: 11,
      topRight: 12,
      bottomLeft: 23,
      bottomRight: 24,
    });
  });

  it("returns hip and ankle indices for bottoms", () => {
    const result = getCategoryLandmarks("bottoms");
    expect(result).toEqual({
      topLeft: 23,
      topRight: 24,
      bottomLeft: 27,
      bottomRight: 28,
    });
  });

  it("returns ankle and foot indices for shoes", () => {
    const result = getCategoryLandmarks("shoes");
    expect(result).toEqual({
      topLeft: 27,
      topRight: 28,
      bottomLeft: 31,
      bottomRight: 32,
    });
  });
});

describe("computeAffineTransform", () => {
  it("computes position, size, and rotation for a rectangular region", () => {
    const landmarks: PoseLandmark[] = Array(33).fill(makeLandmark(0, 0));
    // Shoulders at (0.3, 0.3) and (0.7, 0.3), hips at (0.3, 0.6) and (0.7, 0.6)
    landmarks[11] = makeLandmark(0.3, 0.3);
    landmarks[12] = makeLandmark(0.7, 0.3);
    landmarks[23] = makeLandmark(0.3, 0.6);
    landmarks[24] = makeLandmark(0.7, 0.6);

    const result = computeAffineTransform(landmarks, "tops", 1920, 1080);
    expect(result).not.toBeNull();
    expect(result!.x).toBeCloseTo(960, 0); // center x
    expect(result!.y).toBeCloseTo(486, 0); // center y
    expect(result!.width).toBeGreaterThan(0);
    expect(result!.height).toBeGreaterThan(0);
  });

  it("returns null when landmarks have low visibility", () => {
    const landmarks: PoseLandmark[] = Array(33).fill(makeLandmark(0, 0, 0.1));
    const result = computeAffineTransform(landmarks, "tops", 1920, 1080);
    expect(result).toBeNull();
  });
});
