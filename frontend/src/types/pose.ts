export interface PoseLandmark {
  x: number; // 0-1 normalized
  y: number; // 0-1 normalized
  z: number;
  visibility: number; // 0-1 confidence
}

export interface PoseResult {
  landmarks: PoseLandmark[];
  timestamp: number;
}

// BlazePose landmark indices for clothing overlay
export const POSE_LANDMARKS = {
  LEFT_SHOULDER: 11,
  RIGHT_SHOULDER: 12,
  LEFT_HIP: 23,
  RIGHT_HIP: 24,
  LEFT_KNEE: 25,
  RIGHT_KNEE: 26,
  LEFT_ANKLE: 27,
  RIGHT_ANKLE: 28,
  LEFT_HEEL: 29,
  RIGHT_HEEL: 30,
  LEFT_FOOT_INDEX: 31,
  RIGHT_FOOT_INDEX: 32,
} as const;
