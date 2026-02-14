import { describe, it, expect } from "vitest";
import { findUnoccupiedPosition } from "@/components/mirror/MiraAvatar";

describe("findUnoccupiedPosition", () => {
  it("returns a corner position when no overlays exist", () => {
    const pos = findUnoccupiedPosition([], 1920, 1080, 250, 250);
    expect(pos.x).toBeGreaterThanOrEqual(0);
    expect(pos.y).toBeGreaterThanOrEqual(0);
    expect(pos.x + 250).toBeLessThanOrEqual(1920);
    expect(pos.y + 250).toBeLessThanOrEqual(1080);
  });

  it("avoids occupied regions", () => {
    // Overlay in top-left quadrant
    const occupiedRegions = [{ x: 100, y: 100, width: 400, height: 400 }];
    const pos = findUnoccupiedPosition(occupiedRegions, 1920, 1080, 250, 250);
    // Should not overlap with occupied region
    const overlaps =
      pos.x < 500 && pos.x + 250 > 100 && pos.y < 500 && pos.y + 250 > 100;
    expect(overlaps).toBe(false);
  });
});
