const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface AvatarResult {
  imageBase64: string;
  mimeType: string;
}

/**
 * Generate a Memoji-style avatar via the backend Gemini endpoint.
 * Optionally pass a webcam frame (base64, no data-URI prefix) as reference.
 */
export async function generateAvatar(
  prompt: string,
  webcamFrameBase64?: string
): Promise<AvatarResult> {
  const body: Record<string, unknown> = { prompt };
  if (webcamFrameBase64) {
    body.image = { data: webcamFrameBase64, mimeType: "image/jpeg" };
  }

  const res = await fetch(`${API_URL}/avatar/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Avatar generation failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Generate speech audio via the backend ElevenLabs endpoint.
 * Returns raw audio/mpeg bytes as an ArrayBuffer (ready for Web Audio).
 */
export async function generateSpeech(
  text: string,
  voiceId?: string,
  model?: string
): Promise<ArrayBuffer> {
  const body: Record<string, string> = { text };
  if (voiceId) body.voiceId = voiceId;
  if (model) body.model = model;

  const res = await fetch(`${API_URL}/tts/speak`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `TTS failed: ${res.status}`);
  }

  return res.arrayBuffer();
}
