"""Extract purchase data from receipt emails using LLM extraction.

Extracts ALL purchase items (fashion and non-fashion) and flags each with is_fashion.
"""

import json
import logging
import os
import re

import anthropic

from agent.prompts import _NON_FASHION_BRANDS

logger = logging.getLogger(__name__)

# Known receipt sender patterns (lowercase substrings)
RECEIPT_SENDERS = [
    # Major retailers
    "amazon.com",
    "noreply@zara.com",
    "nordstrom.com",
    "nike.com",
    "uniqlo.com",
    "hm.com",
    "aritzia.com",
    "gap.com",
    "macys.com",
    "urbanoutfitters.com",
    "asos.com",
    "ssense.com",
    "farfetch.com",
    "net-a-porter.com",
    "shopify.com",
    "etsy.com",
    "ebay.com",
    "stockx.com",
    "goat.com",
    "depop.com",
    "poshmark.com",
    "grailed.com",
    "thredup.com",
    "mrporter.com",
    "revolve.com",
    "shein.com",
    "target.com",
    "walmart.com",
    "chewy.com",
    # Generic transactional sender prefixes
    "store-news@",
    "order-update@",
    "orders@",
    "order@",
    "receipt@",
    "receipts@",
    "confirmation@",
    "noreply@",
    "no-reply@",
    "store@",
    "shipping@",
    "ship-confirm@",
    "notify@",
    "notifications@",
]

# Known brand names for matching
KNOWN_BRANDS = [
    "Nike", "Adidas", "Zara", "H&M", "Uniqlo", "Aritzia", "Nordstrom",
    "Gap", "Levi's", "Patagonia", "The North Face", "Lululemon",
    "Gucci", "Prada", "Balenciaga", "Supreme", "Off-White", "Stussy",
    "Carhartt", "Ralph Lauren", "Calvin Klein", "Tommy Hilfiger",
    "AllSaints", "Mango", "COS", "SSENSE", "Everlane", "Reformation",
    "Shein", "Target", "Walmart", "GOAT", "StockX", "Depop",
    "Poshmark", "Revolve", "Theory", "Vince", "Sandro", "Maje",
    "Acne Studios", "AMI Paris", "A.P.C.", "& Other Stories",
    "Cos", "Anthropologie", "Free People", "Urban Outfitters",
]

# Order status detection
STATUS_PATTERN = re.compile(
    r"(order confirmed|shipped|delivered|out for delivery|in transit)", re.I
)

# Tracking number extraction
TRACKING_PATTERN = re.compile(
    r"(?:tracking|track)[^\d]*(\b[A-Z0-9]{10,30}\b)", re.I
)

# Merchant detection from sender domain
MERCHANT_PATTERN = re.compile(r"@([\w.-]+\.\w+)")


def _is_receipt(email: dict) -> bool:
    """Check if email is likely a receipt based on sender OR subject keywords.

    Either signal is sufficient — emails with neither are rejected.
    """
    sender = email.get("sender", "").lower()
    subject = email.get("subject", "").lower()
    receipt_keywords = ["order", "receipt", "confirmation", "shipped", "purchase"]
    sender_match = any(pattern in sender for pattern in RECEIPT_SENDERS)
    subject_match = any(kw in subject for kw in receipt_keywords)
    return sender_match or subject_match


def _detect_brand(text: str, sender: str) -> str:
    """Detect the most likely brand from text content and sender."""
    for brand in KNOWN_BRANDS:
        if brand.lower() in text.lower() or brand.lower() in sender.lower():
            return brand
    match = re.search(r"@([\w.-]+)", sender)
    if match:
        parts = match.group(1).split(".")
        # Use primary domain name, not subdomain (e.g. "nike" from "mail.nike.com")
        domain_name = parts[-2] if len(parts) >= 3 else parts[0]
        return domain_name.capitalize()
    return "Unknown"


def _detect_merchant(sender: str) -> str | None:
    """Extract merchant name from sender email domain."""
    match = MERCHANT_PATTERN.search(sender)
    if match:
        domain = match.group(1).lower()
        # Map known domains to clean merchant names
        merchant_map = {
            "amazon.com": "Amazon",
            "nordstrom.com": "Nordstrom",
            "macys.com": "Macy's",
            "target.com": "Target",
            "walmart.com": "Walmart",
            "shopify.com": "Shopify",
            "etsy.com": "Etsy",
            "ebay.com": "eBay",
            "ssense.com": "SSENSE",
            "farfetch.com": "Farfetch",
            "net-a-porter.com": "Net-a-Porter",
            "mrporter.com": "Mr Porter",
            "asos.com": "ASOS",
            "revolve.com": "Revolve",
            "stockx.com": "StockX",
            "goat.com": "GOAT",
            "depop.com": "Depop",
            "poshmark.com": "Poshmark",
            "grailed.com": "Grailed",
            "thredup.com": "ThredUp",
            "shein.com": "Shein",
        }
        for pattern, name in merchant_map.items():
            if pattern in domain:
                return name
        # Fallback: capitalize the primary domain name (not subdomain)
        parts = domain.split(".")
        domain_name = parts[-2] if len(parts) >= 3 else parts[0]
        return domain_name.capitalize()
    return None


def _extract_order_status(text: str) -> str | None:
    """Extract order status from email text."""
    match = STATUS_PATTERN.search(text)
    if match:
        status = match.group(1).lower()
        # Normalize to simple status values
        if "confirmed" in status:
            return "confirmed"
        if "shipped" in status or "in transit" in status:
            return "shipped"
        if "delivered" in status or "out for delivery" in status:
            return "delivered"
    return None


def _extract_tracking(text: str) -> str | None:
    """Extract tracking number from email text."""
    match = TRACKING_PATTERN.search(text)
    return match.group(1) if match else None


def _categorize_item(item_name: str) -> str | None:
    """Rough category assignment based on item name keywords."""
    name = item_name.lower()

    # Exclude false positives from financial/marketing language
    exclusions = [
        "short selling", "short position", "top picks", "top rated",
        "top stories", "top news", "top 10", "top five", "top deal",
        "boot camp", "bootcamp", "bootstrap",
        "jacket cover", "dust jacket",
    ]
    if any(exc in name for exc in exclusions):
        return None

    categories = {
        "shoes": ["shoe", "sneaker", "boot", "sandal", "air max", "jordan", "runner"],
        "tops": ["shirt", "tee", "top", "blouse", "sweater", "hoodie", "jacket", "blazer", "coat"],
        "bottoms": ["pant", "jean", "short", "skirt", "trouser", "legging"],
        "outerwear": ["jacket", "coat", "parka", "blazer", "vest"],
        "accessories": ["hat", "cap", "belt", "bag", "scarf", "watch", "sunglasses", "jewelry"],
        "dresses": ["dress", "romper", "jumpsuit"],
    }
    for cat, keywords in categories.items():
        if any(kw in name for kw in keywords):
            return cat
    return None


def _extract_with_llm(email: dict) -> list[dict]:
    """Use Claude Haiku to extract ALL purchase items from receipt emails.

    Primary extraction method for all receipt emails. Returns items with
    an is_fashion flag for downstream filtering.
    """
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    if not auth_token:
        logger.warning("ANTHROPIC_AUTH_TOKEN not set — skipping LLM extraction")
        return []

    subject = email.get("subject", "")
    body = email.get("body", "")[:2000]

    prompt = (
        "Extract ALL purchase items from this receipt email. Include every product "
        "purchased: clothing, shoes, accessories, electronics, food, subscriptions, everything.\n\n"
        "For each item, determine if it is a FASHION item (clothing, shoes, bags, jewelry, "
        "accessories, beauty/grooming). Set is_fashion to true for fashion items, false otherwise.\n\n"
        "Return a JSON object with a single key \"items\" containing an array. "
        "Each item should have: brand (string), merchant (string or null), "
        "item_name (string), price (number or null), currency (string, default \"USD\"), "
        "order_status (string or null: confirmed/shipped/delivered), "
        "is_fashion (boolean).\n\n"
        "If no purchase items can be extracted, return {\"items\": []}.\n\n"
        f"Subject: {subject}\n\nBody:\n{body}"
    )

    try:
        client = anthropic.Anthropic(
            auth_token=auth_token,
            default_headers={"anthropic-beta": "oauth-2025-04-20"},
            default_query={"beta": "true"},
        )
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        content = message.content[0].text
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                data = json.loads(content[start:end])
            else:
                return []
        return data.get("items", [])
    except Exception as e:
        logger.warning("LLM extraction failed: %s", e)
        return []


def extract_purchases(email: dict) -> list[dict]:
    """Extract ALL purchase items from a receipt email via LLM.

    Each item includes an is_fashion flag for downstream filtering.
    Returns list of dicts with: brand, merchant, item_name, category, price, date,
    order_status, tracking_number, receipt_text, source_email_id, is_fashion
    """
    if not _is_receipt(email):
        return []

    body = email.get("body", "")
    subject = email.get("subject", "")
    sender = email.get("sender", "")
    full_text = f"{subject}\n{body}"

    brand = _detect_brand(full_text, sender)
    merchant = _detect_merchant(sender)
    order_status = _extract_order_status(full_text)
    tracking_number = _extract_tracking(full_text)
    receipt_text = full_text[:500] if full_text else None

    # LLM extraction for all emails
    llm_items = _extract_with_llm(email)

    purchases = []
    for item in llm_items:
        item_name = item.get("item_name", "")
        if not item_name or len(item_name) < 3:
            continue

        # LLM provides is_fashion; fallback to heuristic if missing
        is_fashion = item.get("is_fashion")
        if is_fashion is None:
            item_brand = (item.get("brand") or brand).lower()
            is_fashion = (
                item_brand not in _NON_FASHION_BRANDS
                and _categorize_item(item_name) is not None
            )

        purchases.append({
            "brand": item.get("brand") or brand,
            "merchant": item.get("merchant") or merchant,
            "item_name": item_name,
            "category": _categorize_item(item_name),
            "price": item.get("price"),
            "date": email.get("date"),
            "order_status": item.get("order_status") or order_status,
            "tracking_number": tracking_number,
            "receipt_text": receipt_text,
            "source_email_id": email.get("message_id"),
            "is_fashion": bool(is_fashion),
        })
    return purchases
