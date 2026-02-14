/**
 * Capture a JPEG snapshot from a video element or canvas.
 */
export function compressSnapshot(
  source: HTMLCanvasElement | HTMLVideoElement,
  quality: number = 0.7
): string {
  let canvas: HTMLCanvasElement;

  if (source instanceof HTMLVideoElement) {
    canvas = document.createElement("canvas");
    canvas.width = source.videoWidth;
    canvas.height = source.videoHeight;
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(source, 0, 0);
  } else {
    canvas = source;
  }

  return canvas.toDataURL("image/jpeg", quality);
}

/**
 * Capture snapshot from a video element, stripping the data URL prefix.
 * Returns raw base64 string suitable for sending to backend.
 */
export function captureBase64Snapshot(
  video: HTMLVideoElement,
  quality: number = 0.7
): string {
  const dataUrl = compressSnapshot(video, quality);
  return dataUrl.replace(/^data:image\/jpeg;base64,/, "");
}
