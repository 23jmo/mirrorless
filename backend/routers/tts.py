"""Text-to-speech endpoint: ElevenLabs TTS API."""

import os

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

load_dotenv()

router = APIRouter(prefix="/tts", tags=["tts"])

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech"


class TTSRequest(BaseModel):
    text: str
    voiceId: str = "9BWtsMINqrJLrRacOk9x"  # Aria
    model: str = "eleven_multilingual_v2"


@router.post("/speak")
async def speak(body: TTSRequest):
    """Convert text to speech via ElevenLabs, return raw audio/mpeg."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ELEVENLABS_TTS_URL}/{body.voiceId}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": body.text,
                    "model_id": body.model,
                },
                timeout=30.0,
            )
            response.raise_for_status()

        return Response(content=response.content, media_type="audio/mpeg")

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"ElevenLabs API error: {exc.response.text}",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
