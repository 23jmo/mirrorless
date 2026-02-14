import type { PoseLandmark } from "@/types/pose";
import { POSE_LANDMARKS } from "@/types/pose";
import type { ClothingCategory } from "@/types/outfit";

export interface PixelCoord {
  x: number;
  y: number;
}

export interface AffineTransform {
  x: number;      // center x in pixels
  y: number;      // center y in pixels
  width: number;  // width in pixels
  height: number; // height in pixels
  rotation: number; // radians
}

interface CategoryLandmarkIndices {
  topLeft: number;
  topRight: number;
  bottomLeft: number;
  bottomRight: number;
}

const MIN_VISIBILITY = 0.5;
const PADDING_FACTOR = 1.15; // 15% padding around clothing

export function getLandmarkPixelCoords(
  landmark: PoseLandmark,
  canvasWidth: number,
  canvasHeight: number
): PixelCoord {
  return {
    x: landmark.x * canvasWidth,
    y: landmark.y * canvasHeight,
  };
}

export function getCategoryLandmarks(category: ClothingCategory): CategoryLandmarkIndices {
  switch (category) {
    case "tops":
    case "outerwear":
      return {
        topLeft: POSE_LANDMARKS.LEFT_SHOULDER,
        topRight: POSE_LANDMARKS.RIGHT_SHOULDER,
        bottomLeft: POSE_LANDMARKS.LEFT_HIP,
        bottomRight: POSE_LANDMARKS.RIGHT_HIP,
      };
    case "bottoms":
      return {
        topLeft: POSE_LANDMARKS.LEFT_HIP,
        topRight: POSE_LANDMARKS.RIGHT_HIP,
        bottomLeft: POSE_LANDMARKS.LEFT_ANKLE,
        bottomRight: POSE_LANDMARKS.RIGHT_ANKLE,
      };
    case "shoes":
      return {
        topLeft: POSE_LANDMARKS.LEFT_ANKLE,
        topRight: POSE_LANDMARKS.RIGHT_ANKLE,
        bottomLeft: POSE_LANDMARKS.LEFT_FOOT_INDEX,
        bottomRight: POSE_LANDMARKS.RIGHT_FOOT_INDEX,
      };
    case "dresses":
      return {
        topLeft: POSE_LANDMARKS.LEFT_SHOULDER,
        topRight: POSE_LANDMARKS.RIGHT_SHOULDER,
        bottomLeft: POSE_LANDMARKS.LEFT_KNEE,
        bottomRight: POSE_LANDMARKS.RIGHT_KNEE,
      };
    case "accessories":
    default:
      return {
        topLeft: POSE_LANDMARKS.LEFT_SHOULDER,
        topRight: POSE_LANDMARKS.RIGHT_SHOULDER,
        bottomLeft: POSE_LANDMARKS.LEFT_HIP,
        bottomRight: POSE_LANDMARKS.RIGHT_HIP,
      };
  }
}

export function computeAffineTransform(
  landmarks: PoseLandmark[],
  category: ClothingCategory,
  canvasWidth: number,
  canvasHeight: number
): AffineTransform | null {
  const indices = getCategoryLandmarks(category);

  const tl = landmarks[indices.topLeft];
  const tr = landmarks[indices.topRight];
  const bl = landmarks[indices.bottomLeft];
  const br = landmarks[indices.bottomRight];

  // Check visibility
  if (
    tl.visibility < MIN_VISIBILITY ||
    tr.visibility < MIN_VISIBILITY ||
    bl.visibility < MIN_VISIBILITY ||
    br.visibility < MIN_VISIBILITY
  ) {
    return null;
  }

  const tlPx = getLandmarkPixelCoords(tl, canvasWidth, canvasHeight);
  const trPx = getLandmarkPixelCoords(tr, canvasWidth, canvasHeight);
  const blPx = getLandmarkPixelCoords(bl, canvasWidth, canvasHeight);
  const brPx = getLandmarkPixelCoords(br, canvasWidth, canvasHeight);

  // Center
  const cx = (tlPx.x + trPx.x + blPx.x + brPx.x) / 4;
  const cy = (tlPx.y + trPx.y + blPx.y + brPx.y) / 4;

  // Width = average of top and bottom edges
  const topWidth = Math.hypot(trPx.x - tlPx.x, trPx.y - tlPx.y);
  const bottomWidth = Math.hypot(brPx.x - blPx.x, brPx.y - blPx.y);
  const width = ((topWidth + bottomWidth) / 2) * PADDING_FACTOR;

  // Height = average of left and right edges
  const leftHeight = Math.hypot(blPx.x - tlPx.x, blPx.y - tlPx.y);
  const rightHeight = Math.hypot(brPx.x - trPx.x, brPx.y - trPx.y);
  const height = ((leftHeight + rightHeight) / 2) * PADDING_FACTOR;

  // Rotation from top edge
  const rotation = Math.atan2(trPx.y - tlPx.y, trPx.x - tlPx.x);

  return { x: cx, y: cy, width, height, rotation };
}
