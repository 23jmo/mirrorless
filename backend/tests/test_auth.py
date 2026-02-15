"""Tests for auth service: user upsert and profile update."""

import json
import os
import uuid

import pytest
import pytest_asyncio
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Reuse NeonSQL helper from test_database
from tests.test_database import NeonSQL, DATABASE_URL


@pytest_asyncio.fixture(scope="session")
async def db():
    return NeonSQL(DATABASE_URL)


@pytest_asyncio.fixture
async def test_email():
    """Generate a unique test email."""
    return f"auth_test_{uuid.uuid4().hex[:8]}@mirrorless.test"


async def test_upsert_creates_new_user(db, test_email):
    """Upsert inserts a new user when email doesn't exist."""
    oauth_json = json.dumps({"access_token": "tok_abc", "refresh_token": "ref_abc"})

    rows = await db.execute(
        """
        INSERT INTO users (name, email, google_oauth_token)
        VALUES ($1, $2, $3::jsonb)
        ON CONFLICT (email) DO UPDATE
          SET name = EXCLUDED.name,
              google_oauth_token = EXCLUDED.google_oauth_token
        RETURNING id, name, email, phone, poke_id
        """,
        ["New User", test_email, oauth_json],
    )
    assert len(rows) == 1
    assert rows[0]["name"] == "New User"
    assert rows[0]["email"] == test_email
    assert rows[0]["phone"] is None

    # Clean up
    await db.execute("DELETE FROM users WHERE email = $1", [test_email])


async def test_upsert_updates_existing_user(db, test_email):
    """Upsert updates tokens for an existing user."""
    oauth_v1 = json.dumps({"access_token": "tok_v1"})
    oauth_v2 = json.dumps({"access_token": "tok_v2"})

    # First insert
    await db.execute(
        """
        INSERT INTO users (name, email, google_oauth_token)
        VALUES ($1, $2, $3::jsonb)
        ON CONFLICT (email) DO UPDATE
          SET name = EXCLUDED.name,
              google_oauth_token = EXCLUDED.google_oauth_token
        RETURNING id
        """,
        ["User V1", test_email, oauth_v1],
    )

    # Second upsert with same email
    rows = await db.execute(
        """
        INSERT INTO users (name, email, google_oauth_token)
        VALUES ($1, $2, $3::jsonb)
        ON CONFLICT (email) DO UPDATE
          SET name = EXCLUDED.name,
              google_oauth_token = EXCLUDED.google_oauth_token
        RETURNING id, name, email, google_oauth_token
        """,
        ["User V2", test_email, oauth_v2],
    )
    assert rows[0]["name"] == "User V2"
    token = rows[0]["google_oauth_token"]
    if isinstance(token, str):
        token = json.loads(token)
    assert token["access_token"] == "tok_v2"

    # Clean up
    await db.execute("DELETE FROM users WHERE email = $1", [test_email])


async def test_profile_update(db):
    """Can update name and phone for an existing user."""
    email = f"profile_{uuid.uuid4().hex[:8]}@mirrorless.test"
    rows = await db.execute(
        "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id",
        ["Original Name", email],
    )
    user_id = rows[0]["id"]

    updated = await db.execute(
        """
        UPDATE users SET name = $1, phone = $2
        WHERE id = $3::uuid
        RETURNING id, name, email, phone, poke_id
        """,
        ["Updated Name", "+12128675309", user_id],
    )
    assert updated[0]["name"] == "Updated Name"
    assert updated[0]["phone"] == "+12128675309"

    # Clean up
    await db.execute("DELETE FROM users WHERE id = $1", [user_id])


async def test_profile_update_nonexistent_user(db):
    """Profile update returns empty for a non-existent user ID."""
    fake_id = str(uuid.uuid4())
    rows = await db.execute(
        """
        UPDATE users SET name = $1, phone = $2
        WHERE id = $3::uuid
        RETURNING id
        """,
        ["Nobody", "+10000000000", fake_id],
    )
    assert len(rows) == 0


async def test_profile_update_with_e164_phone(db):
    """Phone numbers are stored in E.164 format."""
    from fastapi.testclient import TestClient
    from main import app

    # Create test user
    email = f"phone_{uuid.uuid4().hex[:8]}@mirrorless.test"
    rows = await db.execute(
        "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id",
        ["Phone User", email],
    )
    user_id = rows[0]["id"]

    client = TestClient(app)

    # Test various phone formats - all should normalize to E.164
    # Use realistic phone number (212-867-5309 validates successfully)
    test_cases = [
        ("212-867-5309", "+12128675309"),  # US format with dashes
        ("(212) 867-5309", "+12128675309"),  # US format with parens
        ("+1 212 867 5309", "+12128675309"),  # E.164 with spaces
        ("+12128675309", "+12128675309"),  # Already E.164
    ]

    for input_phone, expected_e164 in test_cases:
        response = client.post(
            "/auth/profile",
            json={"user_id": user_id, "name": "Phone User", "phone": input_phone}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == expected_e164, f"Input {input_phone} should normalize to {expected_e164}"

    # Clean up
    await db.execute("DELETE FROM users WHERE id = $1", [user_id])


async def test_profile_update_invalid_phone(db):
    """Invalid phone numbers return 400 error."""
    from fastapi.testclient import TestClient
    from main import app

    # Create test user
    email = f"invalid_phone_{uuid.uuid4().hex[:8]}@mirrorless.test"
    rows = await db.execute(
        "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id",
        ["Invalid Phone User", email],
    )
    user_id = rows[0]["id"]

    client = TestClient(app)

    # Test invalid phone formats
    invalid_phones = [
        "1234",  # Too short
        "abc-def-ghij",  # Non-numeric
        "555",  # Way too short
        "+999999999999999999",  # Invalid country code
    ]

    for invalid_phone in invalid_phones:
        response = client.post(
            "/auth/profile",
            json={"user_id": user_id, "name": "Invalid Phone User", "phone": invalid_phone}
        )
        assert response.status_code == 400, f"Phone {invalid_phone} should be rejected"
        assert "Invalid phone number" in response.json()["detail"]

    # Clean up
    await db.execute("DELETE FROM users WHERE id = $1", [user_id])


async def test_profile_update_empty_phone(db):
    """Empty phone string returns 400 error."""
    from fastapi.testclient import TestClient
    from main import app

    # Create test user
    email = f"empty_phone_{uuid.uuid4().hex[:8]}@mirrorless.test"
    rows = await db.execute(
        "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id",
        ["Empty Phone User", email],
    )
    user_id = rows[0]["id"]

    client = TestClient(app)

    response = client.post(
        "/auth/profile",
        json={"user_id": user_id, "name": "Empty Phone User", "phone": "   "}
    )
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]

    # Clean up
    await db.execute("DELETE FROM users WHERE id = $1", [user_id])
