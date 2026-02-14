"""Tests for Gmail message fetching."""

import pytest
from unittest.mock import MagicMock, patch
from scraper.gmail_fetch import search_emails, get_message_content


def test_search_emails_returns_message_ids():
    """search_emails queries Gmail and returns list of message IDs."""
    svc = MagicMock()
    list_mock = MagicMock()
    list_mock.execute.return_value = {
        "messages": [{"id": "msg1"}, {"id": "msg2"}],
        "resultSizeEstimate": 2,
    }
    svc.users.return_value.messages.return_value.list.return_value = list_mock

    result = search_emails(svc, query="from:noreply@amazon.com", max_results=10)
    assert result == ["msg1", "msg2"]


def test_search_emails_empty():
    """search_emails returns empty list when no matches."""
    svc = MagicMock()
    list_mock = MagicMock()
    list_mock.execute.return_value = {"resultSizeEstimate": 0}
    svc.users.return_value.messages.return_value.list.return_value = list_mock

    result = search_emails(svc, query="nonexistent", max_results=5)
    assert result == []


def test_get_message_content_extracts_subject_and_body():
    """get_message_content returns subject, sender, date, and body text."""
    svc = MagicMock()
    get_mock = MagicMock()
    get_mock.execute.return_value = {
        "id": "msg1",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Your order has shipped!"},
                {"name": "From", "value": "noreply@amazon.com"},
                {"name": "Date", "value": "Mon, 10 Feb 2026 12:00:00 -0800"},
            ],
            "mimeType": "text/plain",
            "body": {"data": "WW91ciBvcmRlciBoYXMgc2hpcHBlZCE="},  # base64 "Your order has shipped!"
        },
    }
    svc.users.return_value.messages.return_value.get.return_value = get_mock

    result = get_message_content(svc, "msg1")
    assert result["subject"] == "Your order has shipped!"
    assert result["sender"] == "noreply@amazon.com"
    assert "shipped" in result["body"]
    assert result["message_id"] == "msg1"
