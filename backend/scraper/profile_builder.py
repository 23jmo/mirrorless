"""Build a style profile from purchase data and brand frequencies."""

from collections import Counter

from agent.prompts import _filter_fashion_purchases

# Map categories to style tags
CATEGORY_STYLE_MAP = {
    "shoes": ["sneakerhead", "athletic"],
    "tops": ["casual"],
    "bottoms": ["casual"],
    "outerwear": ["layered", "polished"],
    "accessories": ["accessorized"],
    "dresses": ["feminine", "occasion-ready"],
}

# Map price ranges to style tags
PRICE_STYLE_MAP = [
    (0, 50, "budget-friendly"),
    (50, 150, "mid-range"),
    (150, 500, "premium"),
    (500, float("inf"), "luxury"),
]


def _build_enhanced_narrative(
    purchases: list[dict],
    brands: list[str],
    brand_counts: Counter,
    price_range: dict,
    category_counts: Counter,
) -> str:
    """Build a rich narrative summary with brand loyalty, frequency, and spending patterns."""
    parts = []

    # Brand loyalty pattern
    top_brands_str = ", ".join(brands[:3]) if brands else "various brands"
    if brands and brand_counts:
        top_brand = brands[0]
        top_count = brand_counts[top_brand]
        total_items = sum(brand_counts.values())
        loyalty_pct = (top_count / total_items * 100) if total_items > 0 else 0

        if loyalty_pct > 40:
            parts.append(f"Loyal to {top_brand} ({loyalty_pct:.0f}% of purchases).")
        elif loyalty_pct > 25:
            parts.append(f"Leans toward {top_brand}, but also shops at {', '.join(brands[1:3])}.")
        else:
            parts.append(f"Diverse shopper across {top_brands_str} and others.")
    else:
        parts.append(f"Shops at {top_brands_str}.")

    # Shopping frequency (items per month)
    if purchases:
        dates = [p.get("date") for p in purchases if p.get("date")]
        if len(dates) >= 2:
            from datetime import datetime
            parsed_dates = []
            for d in dates:
                try:
                    parsed_dates.append(datetime.strptime(str(d)[:10], "%Y-%m-%d"))
                except ValueError:
                    continue
            if len(parsed_dates) >= 2:
                date_range_days = (max(parsed_dates) - min(parsed_dates)).days
                if date_range_days > 0:
                    months = max(date_range_days / 30, 1)
                    items_per_month = len(purchases) / months
                    if items_per_month > 8:
                        parts.append(f"Heavy shopper (~{items_per_month:.0f} items/month).")
                    elif items_per_month > 3:
                        parts.append(f"Regular shopper (~{items_per_month:.0f} items/month).")
                    else:
                        parts.append(f"Selective shopper (~{items_per_month:.1f} items/month).")

    # Splurge vs basics pattern
    prices = [p["price"] for p in purchases if p.get("price") is not None]
    if prices and price_range.get("avg", 0) > 0:
        avg = price_range["avg"]
        splurge_count = sum(1 for p in prices if p > avg * 2)
        basics_count = sum(1 for p in prices if p < avg * 0.5)
        total = len(prices)

        if splurge_count > total * 0.2:
            parts.append(f"Splurge-prone — {splurge_count} items over 2x their average (${avg:.0f}).")
        elif basics_count > total * 0.5:
            parts.append(f"Basics-focused — most items well under the ${avg:.0f} average.")
        else:
            parts.append(f"Balanced spender around ${avg:.0f} per item.")

    # Category summary
    cat_summary = ", ".join(
        f"{cat} ({count})" for cat, count in category_counts.most_common(3)
    )
    if cat_summary:
        parts.append(f"Most purchased: {cat_summary}.")

    return " ".join(parts)


def build_style_profile(
    purchases: list[dict],
    brand_freq: dict[str, int],
) -> dict:
    """Aggregate purchases and brand frequencies into a style profile.

    Returns dict matching StyleProfileUpdate schema:
    {brands, price_range, style_tags, narrative_summary}
    """
    # Filter to fashion-only items before building profile
    purchases = _filter_fashion_purchases(purchases)

    if not purchases and not brand_freq:
        return {
            "brands": [],
            "price_range": {"min": 0, "max": 0, "avg": 0},
            "style_tags": [],
            "narrative_summary": None,
        }

    # Brands: merge from purchases + frequency scan, ordered by frequency
    brand_counts = Counter(brand_freq)
    for p in purchases:
        brand_counts[p["brand"]] += 1
    brands = [b for b, _ in brand_counts.most_common()]

    # Price range
    prices = [p["price"] for p in purchases if p.get("price") is not None]
    price_range = {
        "min": min(prices) if prices else 0,
        "max": max(prices) if prices else 0,
        "avg": round(sum(prices) / len(prices), 2) if prices else 0,
    }

    # Style tags from categories
    style_tags = set()
    category_counts = Counter(p.get("category") for p in purchases if p.get("category"))
    for cat, count in category_counts.items():
        if cat in CATEGORY_STYLE_MAP:
            style_tags.update(CATEGORY_STYLE_MAP[cat])

    # Style tags from price range
    avg_price = price_range["avg"]
    for low, high, tag in PRICE_STYLE_MAP:
        if low <= avg_price < high:
            style_tags.add(tag)
            break

    # Enhanced narrative
    narrative = _build_enhanced_narrative(
        purchases, brands, brand_counts, price_range, category_counts,
    )

    return {
        "brands": brands,
        "price_range": price_range,
        "style_tags": sorted(style_tags),
        "narrative_summary": narrative,
    }
