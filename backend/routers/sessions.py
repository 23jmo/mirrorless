"""Session endpoints for MCP integration."""

import uuid
from fastapi import APIRouter, HTTPException
from models.database import NeonHTTPClient

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("/{session_id}/info")
async def get_session_info(session_id: str):
    """Get session info including user's phone number.

    Used by Poke to map session_id → phone for save_session calls.

    Returns:
        dict: Session info with session_id, user_id, phone, name, started_at,
              ended_at, and status.

    Raises:
        HTTPException: 400 if session_id is not a valid UUID
        HTTPException: 404 if session not found
    """
    db = NeonHTTPClient()
    try:
        # Validate session_id is valid UUID
        try:
            uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session ID format")

        # Join sessions with users to get phone
        rows = await db.execute(
            """
            SELECT
                s.id as session_id,
                s.user_id,
                u.phone,
                u.name,
                s.started_at,
                s.ended_at,
                s.status
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.id = $1::uuid
            """,
            [session_id],
        )

        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")

        return rows[0]
    finally:
        await db.close()
