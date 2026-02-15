"""Auth endpoints: Google OAuth exchange, profile update, and selfie upload."""

import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.database import NeonHTTPClient
from services.auth import exchange_google_code, upsert_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: str = "postmessage"


class ProfileUpdateRequest(BaseModel):
    user_id: str
    name: str
    phone: Optional[str] = None


class SelfieUploadRequest(BaseModel):
    user_id: str
    selfie_base64: str


@router.post("/google")
async def google_login(body: GoogleAuthRequest):
    """Exchange a Google auth code for tokens, upsert user, return profile."""
    db = NeonHTTPClient()
    try:
        token_data = await exchange_google_code(body.code, body.redirect_uri)
        user = await upsert_user(db, token_data)
        return user
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        await db.close()


@router.post("/profile")
async def update_profile(body: ProfileUpdateRequest):
    """Update user name and optionally phone number."""
    db = NeonHTTPClient()
    try:
        if body.phone is not None:
            rows = await db.execute(
                """
                UPDATE users SET name = $1, phone = $2
                WHERE id = $3::uuid
                RETURNING id, name, email, phone, poke_id
                """,
                [body.name, body.phone, body.user_id],
            )
        else:
            rows = await db.execute(
                """
                UPDATE users SET name = $1
                WHERE id = $2::uuid
                RETURNING id, name, email, phone, poke_id
                """,
                [body.name, body.user_id],
            )
        if not rows:
            raise HTTPException(status_code=404, detail="User not found")
        return rows[0]
    finally:
        await db.close()


@router.post("/selfie")
async def upload_selfie(body: SelfieUploadRequest):
    """Store a base64-encoded selfie image for the user."""
    # Strip data-URI prefix if the frontend sends the full data URL
    selfie = re.sub(r"^data:image/\w+;base64,", "", body.selfie_base64)

    db = NeonHTTPClient()
    try:
        rows = await db.execute(
            """
            UPDATE users SET selfie_base64 = $1
            WHERE id = $2::uuid
            RETURNING id, name, email, phone, poke_id
            """,
            [selfie, body.user_id],
        )
        if not rows:
            raise HTTPException(status_code=404, detail="User not found")
        return rows[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to save selfie for user %s", body.user_id)
        raise HTTPException(status_code=500, detail=f"Failed to save selfie: {exc}")
    finally:
        await db.close()
