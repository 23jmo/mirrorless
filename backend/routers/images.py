"""Image processing endpoints."""

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from services.image_processing import remove_background_from_url

router = APIRouter(prefix="/api/images", tags=["images"])


class RemoveBackgroundRequest(BaseModel):
    image_url: str


@router.post("/remove-background")
async def remove_background(req: RemoveBackgroundRequest):
    """Remove background from a clothing image URL. Returns transparent PNG."""
    try:
        png_bytes = remove_background_from_url(req.image_url)
        return Response(content=png_bytes, media_type="image/png")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Background removal failed: {e}")
