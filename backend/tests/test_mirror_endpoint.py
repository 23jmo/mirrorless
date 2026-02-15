"""Tests for mirror bridge REST endpoints (backend/routers/mirror.py).

These test the FastAPI endpoints that translate HTTP requests into Socket.io emissions.
Socket.io is mocked — we verify the correct events are emitted to the right rooms.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_app():
    """Create a minimal FastAPI app with mirror router and mocked Socket.io."""
    from fastapi import FastAPI
    from routers.mirror import router

    app = FastAPI()
    app.include_router(router)

    # Mock Socket.io server — emit is async, but manager.get_participants is sync
    mock_sio = AsyncMock()
    mock_sio.manager = MagicMock()
    mock_sio.manager.get_participants.return_value = iter([])

    app.state.sio = mock_sio
    return app, mock_sio


@pytest.fixture
def client_and_sio():
    app, mock_sio = _make_app()
    client = TestClient(app)
    return client, mock_sio


def test_present_items_endpoint_emits_socket(client_and_sio):
    """POST /api/mirror/present emits tool_result to correct room."""
    client, mock_sio = client_and_sio

    resp = client.post("/api/mirror/present", json={
        "mirror_id": "MIRROR-A1",
        "items": [
            {
                "title": "Nike Air Max 90",
                "price": "$129.99",
                "image_url": "https://example.com/nike.jpg",
                "link": "https://nike.com/air-max-90",
                "source": "Nike.com",
            }
        ],
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["presented"] == 1

    # Verify Socket.io emit
    mock_sio.emit.assert_called_once()
    call_args = mock_sio.emit.call_args
    assert call_args[0][0] == "tool_result"  # event name
    assert call_args[1]["room"] == "mirror:MIRROR-A1"
    payload = call_args[0][1]
    assert payload["type"] == "clothing_results"
    assert len(payload["items"]) == 1


def test_text_endpoint_emits_socket(client_and_sio):
    """POST /api/mirror/text emits mirror_text to correct room."""
    client, mock_sio = client_and_sio

    resp = client.post("/api/mirror/text", json={
        "mirror_id": "MIRROR-A1",
        "text": "The navy blazer pairs perfectly!",
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True

    mock_sio.emit.assert_called_once()
    call_args = mock_sio.emit.call_args
    assert call_args[0][0] == "mirror_text"
    assert call_args[1]["room"] == "mirror:MIRROR-A1"
    assert call_args[0][1]["text"] == "The navy blazer pairs perfectly!"


def test_present_items_validates_empty_items(client_and_sio):
    """POST /api/mirror/present with empty items returns 422."""
    client, _ = client_and_sio

    resp = client.post("/api/mirror/present", json={
        "mirror_id": "MIRROR-A1",
        "items": [],
    })

    assert resp.status_code == 422


def test_text_endpoint_validates_empty_text(client_and_sio):
    """POST /api/mirror/text with empty text returns 422."""
    client, _ = client_and_sio

    resp = client.post("/api/mirror/text", json={
        "mirror_id": "MIRROR-A1",
        "text": "",
    })

    assert resp.status_code == 422


def test_save_session_writes_to_db(client_and_sio):
    """POST /api/mirror/sessions creates a session record."""
    client, _ = client_and_sio

    with patch("routers.mirror.NeonHTTPClient") as mock_db_cls:
        mock_db = AsyncMock()
        mock_db_cls.return_value = mock_db
        mock_db.execute.side_effect = [
            # First call: INSERT INTO sessions → RETURNING id
            [{"id": "test-session-123"}],
            # Second call: INSERT INTO session_outfits (item 1)
            [],
            # Third call: INSERT INTO session_outfits (summary)
            [],
        ]

        resp = client.post("/api/mirror/sessions", json={
            "mirror_id": "MIRROR-A1",
            "summary": "Looked at sneakers",
            "items_shown": [
                {"title": "Nike AM90", "price": "$129", "reaction": "liked"},
            ],
            "reactions": {"likes": 1, "items_shown": 1},
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["session_id"] == "test-session-123"

        # Verify DB calls were made
        assert mock_db.execute.call_count == 3
        mock_db.close.assert_called_once()


def test_get_sessions_returns_history(client_and_sio):
    """GET /api/mirror/sessions/{mirror_id} returns session list."""
    client, _ = client_and_sio

    with patch("routers.mirror.NeonHTTPClient") as mock_db_cls:
        mock_db = AsyncMock()
        mock_db_cls.return_value = mock_db
        mock_db.execute.side_effect = [
            # First call: SELECT sessions
            [
                {
                    "id": "s1",
                    "started_at": "2026-02-14T10:00:00Z",
                    "ended_at": "2026-02-14T10:15:00Z",
                    "status": "completed",
                },
            ],
            # Second call: SELECT session_outfits for s1
            [
                {"outfit_data": {"title": "Nike AM90"}, "reaction": "liked"},
            ],
        ]

        resp = client.get("/api/mirror/sessions/MIRROR-A1?limit=5")

        assert resp.status_code == 200
        data = resp.json()
        assert data["mirror_id"] == "MIRROR-A1"
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["session_id"] == "s1"
        assert len(data["sessions"][0]["items"]) == 1


def test_get_sessions_empty_history(client_and_sio):
    """GET sessions for unknown mirror returns empty list."""
    client, _ = client_and_sio

    with patch("routers.mirror.NeonHTTPClient") as mock_db_cls:
        mock_db = AsyncMock()
        mock_db_cls.return_value = mock_db
        mock_db.execute.return_value = []

        resp = client.get("/api/mirror/sessions/UNKNOWN-MIRROR")

        assert resp.status_code == 200
        data = resp.json()
        assert data["sessions"] == []


def test_mirror_status_disconnected(client_and_sio):
    """GET /api/mirror/status for unknown mirror returns connected=false."""
    client, mock_sio = client_and_sio

    mock_sio.manager.get_participants.return_value = iter([])

    resp = client.get("/api/mirror/status/UNKNOWN-MIRROR")

    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False


def test_mirror_status_connected(client_and_sio):
    """GET /api/mirror/status for connected mirror returns connected=true."""
    client, mock_sio = client_and_sio

    mock_sio.manager.get_participants.return_value = iter([("some-sid", "/")])

    resp = client.get("/api/mirror/status/MIRROR-A1")

    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
