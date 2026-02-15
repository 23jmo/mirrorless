"""Avatar generation endpoint: Gemini Image API for Memoji-style avatars."""

import base64
import os

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

router = APIRouter(prefix="/avatar", tags=["avatar"])


class ImageInput(BaseModel):
    data: str  # base64-encoded image
    mimeType: str = "image/jpeg"


class AvatarRequest(BaseModel):
    prompt: str
    image: ImageInput | None = None
    model: str = "gemini-2.5-flash-image"


@router.post("/generate")
async def generate_avatar(body: AvatarRequest):
    """Generate a Memoji-style avatar using Gemini's image generation."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    client = genai.Client(api_key=api_key)

    try:
        contents: list = []

        # If a reference image is provided, include it
        if body.image:
            contents.append(
                types.Part.from_bytes(
                    data=__import__("base64").b64decode(body.image.data),
                    mime_type=body.image.mimeType,
                )
            )

        contents.append(body.prompt)

        response = client.models.generate_content(
            model=body.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # Extract image from response
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                # inline_data.data may be raw bytes or base64 string depending on SDK version
                raw = part.inline_data.data
                if isinstance(raw, bytes):
                    image_b64 = base64.b64encode(raw).decode("utf-8")
                else:
                    image_b64 = raw
                return {
                    "imageBase64": image_b64,
                    "mimeType": part.inline_data.mime_type,
                }

        raise HTTPException(
            status_code=500, detail="No image returned from Gemini"
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
