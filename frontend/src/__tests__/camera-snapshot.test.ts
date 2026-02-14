import { describe, it, expect, vi } from "vitest";
import { compressSnapshot, captureBase64Snapshot } from "@/lib/camera-snapshot";

describe("compressSnapshot", () => {
  it("calls toDataURL with jpeg format and quality on a canvas", () => {
    const mockCanvas = {
      toDataURL: vi.fn().mockReturnValue("data:image/jpeg;base64,abc123"),
    } as unknown as HTMLCanvasElement;

    const result = compressSnapshot(mockCanvas, 0.6);
    expect(result).toBe("data:image/jpeg;base64,abc123");
    expect(mockCanvas.toDataURL).toHaveBeenCalledWith("image/jpeg", 0.6);
  });
});

describe("captureBase64Snapshot", () => {
  it("strips the data URL prefix from the result", () => {
    // Create a real video element so instanceof works
    const video = document.createElement("video");
    Object.defineProperty(video, "videoWidth", { value: 640 });
    Object.defineProperty(video, "videoHeight", { value: 480 });

    // Mock the canvas that gets created internally
    const mockToDataURL = vi.fn().mockReturnValue("data:image/jpeg;base64,rawdata");
    const mockDrawImage = vi.fn();
    const mockGetContext = vi.fn().mockReturnValue({ drawImage: mockDrawImage });

    const origCreateElement = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      if (tag === "canvas") {
        return {
          width: 0,
          height: 0,
          getContext: mockGetContext,
          toDataURL: mockToDataURL,
        } as unknown as HTMLCanvasElement;
      }
      return origCreateElement(tag);
    });

    const result = captureBase64Snapshot(video, 0.5);
    expect(result).toBe("rawdata");
    expect(mockDrawImage).toHaveBeenCalledWith(video, 0, 0);

    vi.restoreAllMocks();
  });
});
