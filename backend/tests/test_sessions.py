"""Tests for sessions endpoint: session info for Poke MCP integration."""

import os
import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from main import app
from tests.test_database import NeonSQL, DATABASE_URL

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


@pytest_asyncio.fixture(scope="session")
async def db():
    return NeonSQL(DATABASE_URL)


@pytest_asyncio.fixture
async def test_user_with_session(db):
    """Create a test user with a session and return user_id, session_id, phone."""
    email = f"session_test_{uuid.uuid4().hex[:8]}@mirrorless.test"
    phone = f"+1555{uuid.uuid4().hex[:7]}"  # Unique phone

    # Create user with phone
    user_rows = await db.execute(
        "INSERT INTO users (name, email, phone) VALUES ($1, $2, $3) RETURNING id",
        ["Session User", email, phone],
    )
    user_id = user_rows[0]["id"]

    # Create session
    session_rows = await db.execute(
        """
        INSERT INTO sessions (user_id, started_at, status)
        VALUES ($1::uuid, $2::timestamp, $3)
        RETURNING id
        """,
        [user_id, datetime.now().isoformat(), "active"],
    )
    session_id = session_rows[0]["id"]

    yield {"user_id": user_id, "session_id": session_id, "phone": phone, "email": email}

    # Clean up
    await db.execute("DELETE FROM sessions WHERE id = $1", [session_id])
    await db.execute("DELETE FROM users WHERE id = $1", [user_id])


def test_get_session_info_success(test_user_with_session):
    """GET /api/sessions/{session_id}/info returns correct session info."""
    client = TestClient(app)
    data = test_user_with_session

    response = client.get(f"/api/sessions/{data['session_id']}/info")

    assert response.status_code == 200
    info = response.json()
    assert info["session_id"] == data["session_id"]
    assert info["user_id"] == data["user_id"]
    assert info["phone"] == data["phone"]
    assert info["name"] == "Session User"
    assert info["status"] == "active"
    assert "started_at" in info


def test_get_session_info_not_found():
    """GET /api/sessions/{session_id}/info returns 404 for non-existent session."""
    client = TestClient(app)
    fake_session_id = str(uuid.uuid4())

    response = client.get(f"/api/sessions/{fake_session_id}/info")

    assert response.status_code == 404
    assert "Session not found" in response.json()["detail"]


def test_get_session_info_invalid_uuid():
    """GET /api/sessions/{session_id}/info returns 400 for invalid UUID."""
    client = TestClient(app)

    response = client.get("/api/sessions/not-a-uuid/info")

    assert response.status_code == 400
    assert "Invalid session ID format" in response.json()["detail"]


async def test_get_session_info_user_without_phone(db):
    """Session info returns phone: null for users without phone."""
    email = f"no_phone_{uuid.uuid4().hex[:8]}@mirrorless.test"

    # Create user without phone
    user_rows = await db.execute(
        "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id",
        ["No Phone User", email],
    )
    user_id = user_rows[0]["id"]

    # Create session
    session_rows = await db.execute(
        """
        INSERT INTO sessions (user_id, started_at, status)
        VALUES ($1::uuid, $2::timestamp, $3)
        RETURNING id
        """,
        [user_id, datetime.now().isoformat(), "active"],
    )
    session_id = session_rows[0]["id"]

    client = TestClient(app)
    response = client.get(f"/api/sessions/{session_id}/info")

    assert response.status_code == 200
    info = response.json()
    assert info["phone"] is None  # Should return null for users without phone

    # Clean up
    await db.execute("DELETE FROM sessions WHERE id = $1", [session_id])
    await db.execute("DELETE FROM users WHERE id = $1", [user_id])
