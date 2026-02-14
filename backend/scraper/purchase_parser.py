"""Extract purchase data from receipt emails using pattern matching."""

import re
from datetime import date

# Known receipt sender patterns (lowercase substrings)
RECEIPT_SENDERS = [
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
    "store-news@",
    "order-update@",
    "receipt@",
    "confirmation@",
    "noreply@",
]

# Known brand names for matching
KNOWN_BRANDS = [
    "Nike", "Adidas", "Zara", "H&M", "Uniqlo", "Aritzia", "Nordstrom",
    "Gap", "Levi's", "Patagonia", "The North Face", "Lululemon",
    "Gucci", "Prada", "Balenciaga", "Supreme", "Off-White", "Stussy",
    "Carhartt", "Ralph Lauren", "Calvin Klein", "Tommy Hilfiger",
    "AllSaints", "Mango", "COS", "SSENSE", "Everlane", "Reformation",
]

# Price pattern: $XX.XX or $X,XXX.XX
PRICE_PATTERN = re.compile(r"\$\s?([\d,]+\.?\d{0,2})")

# Item-price line pattern: "item name - $XX.XX" or "item name $XX.XX" or "item name Price: $XX.XX"
ITEM_PRICE_PATTERN = re.compile(
    r"(?:(?:\d+x?\s+)?(.+?))\s*[-–—]?\s*(?:Price:\s*)?\$([\d,]+\.?\d{0,2})"
)


def _is_receipt(email: dict) -> bool:
    """Check if email is likely a receipt based on sender."""
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
        domain = match.group(1).split(".")[0].capitalize()
        return domain
    return "Unknown"


def _parse_price(price_str: str) -> float | None:
    """Parse a price string like '129.99' or '1,299.99' to float."""
    try:
        return float(price_str.replace(",", ""))
    except (ValueError, TypeError):
        return None


def _categorize_item(item_name: str) -> str | None:
    """Rough category assignment based on item name keywords."""
    name = item_name.lower()
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


def extract_purchases(email: dict) -> list[dict]:
    """Extract purchase items from a receipt email.

    Returns list of dicts with: brand, item_name, category, price, date, source_email_id
    """
    if not _is_receipt(email):
        return []

    body = email.get("body", "")
    subject = email.get("subject", "")
    sender = email.get("sender", "")
    full_text = f"{subject}\n{body}"

    brand = _detect_brand(full_text, sender)

    # Try to extract item-price pairs from body
    matches = ITEM_PRICE_PATTERN.findall(body)

    purchases = []
    if matches:
        for item_name, price_str in matches:
            item_name = re.sub(r"^\d+x?\s+", "", item_name.strip()).strip()
            if len(item_name) < 3 or item_name.lower() in ("subtotal", "total", "tax", "shipping"):
                continue
            price = _parse_price(price_str)
            purchases.append({
                "brand": brand,
                "item_name": item_name,
                "category": _categorize_item(item_name),
                "price": price,
                "date": email.get("date"),
                "source_email_id": email.get("message_id"),
            })
    else:
        # Fallback: extract from subject line
        prices = PRICE_PATTERN.findall(full_text)
        price = _parse_price(prices[0]) if prices else None
        item_name = re.sub(
            r"^(your |order |re: |fwd: |amazon\.com order of )",
            "",
            subject,
            flags=re.IGNORECASE,
        ).strip().rstrip(".")
        if item_name:
            purchases.append({
                "brand": brand,
                "item_name": item_name,
                "category": _categorize_item(item_name),
                "price": price,
                "date": email.get("date"),
                "source_email_id": email.get("message_id"),
            })

    return purchases
