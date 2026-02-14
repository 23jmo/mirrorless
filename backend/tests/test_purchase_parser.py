"""Tests for purchase extraction from email content."""

from scraper.purchase_parser import extract_purchases, RECEIPT_SENDERS


def test_receipt_senders_is_nonempty():
    """We have a list of known receipt sender patterns."""
    assert len(RECEIPT_SENDERS) > 0
    assert any("amazon" in s for s in RECEIPT_SENDERS)


def test_extract_purchases_from_amazon_receipt():
    """Extracts brand, item, price from a typical Amazon receipt email."""
    email = {
        "message_id": "msg1",
        "subject": "Your Amazon.com order of Nike Air Max 90...",
        "sender": "auto-confirm@amazon.com",
        "date": "2026-01-15T10:00:00",
        "body": (
            "Hello,\n"
            "Thank you for your order.\n\n"
            "Nike Air Max 90\n"
            "Price: $129.99\n\n"
            "Shipping to: 123 Main St"
        ),
    }
    purchases = extract_purchases(email)
    assert len(purchases) >= 1
    p = purchases[0]
    assert p["brand"] == "Nike"
    assert "Air Max" in p["item_name"]
    assert p["price"] == 129.99
    assert p["source_email_id"] == "msg1"


def test_extract_purchases_non_receipt_returns_empty():
    """Non-receipt emails return empty list."""
    email = {
        "message_id": "msg2",
        "subject": "Meeting tomorrow",
        "sender": "coworker@company.com",
        "date": "2026-01-20T08:00:00",
        "body": "Hey, can we meet at 3pm?",
    }
    purchases = extract_purchases(email)
    assert purchases == []


def test_extract_purchases_handles_multiple_items():
    """Can extract multiple items from a single receipt."""
    email = {
        "message_id": "msg3",
        "subject": "Your Zara order confirmation",
        "sender": "noreply@zara.com",
        "date": "2026-02-01T14:00:00",
        "body": (
            "Order confirmation\n\n"
            "1x Oversized Blazer - $89.90\n"
            "1x Slim Fit Jeans - $49.90\n\n"
            "Subtotal: $139.80"
        ),
    }
    purchases = extract_purchases(email)
    assert len(purchases) >= 2
