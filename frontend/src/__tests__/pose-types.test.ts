import { describe, it, expect } from "vitest";
import { POSE_LANDMARKS } from "@/types/pose";

describe("POSE_LANDMARKS", () => {
  it("has correct landmark indices for clothing overlay", () => {
    expect(POSE_LANDMARKS.LEFT_SHOULDER).toBe(11);
    expect(POSE_LANDMARKS.RIGHT_SHOULDER).toBe(12);
    expect(POSE_LANDMARKS.LEFT_HIP).toBe(23);
    expect(POSE_LANDMARKS.RIGHT_HIP).toBe(24);
    expect(POSE_LANDMARKS.LEFT_ANKLE).toBe(27);
    expect(POSE_LANDMARKS.RIGHT_ANKLE).toBe(28);
  });

  it("has all required body regions for full-body overlay", () => {
    const required = [
      "LEFT_SHOULDER", "RIGHT_SHOULDER",
      "LEFT_HIP", "RIGHT_HIP",
      "LEFT_ANKLE", "RIGHT_ANKLE",
      "LEFT_HEEL", "RIGHT_HEEL",
      "LEFT_FOOT_INDEX", "RIGHT_FOOT_INDEX",
    ];
    for (const key of required) {
      expect(POSE_LANDMARKS).toHaveProperty(key);
    }
  });
});
