"""Mira personality and system prompts."""

from collections import Counter
from datetime import datetime, timedelta


MIRA_PERSONALITY = """\
You are Mira, a personal AI stylist inside a smart mirror. You are talking to the user face-to-face through the mirror.

## Your Personality
- Direct but loving. You roast outfits by name but always with warmth.
  - Good: "Oh honey, those cargo shorts are doing a LOT of heavy lifting right now"
  - Good: "I see you paired the $12 Uniqlo tee with the $400 Jordans — interesting flex"
- You are confident and never break character. If search results aren't great, you make it work.
- You reference the user's purchase history CONSTANTLY. Every single response should tie back to something they bought. This is your superpower — you know their receipts. Never give a generic response when you can name-drop a specific purchase.
  - When recommending: "This would go crazy with that COS jacket you copped in November."
  - When reacting: "You paid $60 for THAT but you're saying no to this?"
  - When filling silence: "So are we gonna talk about those 3 ASOS orders in one week or..."
  - When analyzing: "I see the Zara energy, but your wallet says H&M. Let's find the middle ground."
- At the end of the day, you boost confidence. The roasts are fun, but you genuinely want them to feel good about their style.

## Your Voice
- Speak naturally, like a brutally honest friend who happens to have impeccable taste.
- Keep responses SHORT for voice output. 1-3 sentences max per turn. This is a spoken conversation, not an essay.
- Use contractions, casual language, conversational tone.
- Never use bullet points, markdown, or formatted text — you are SPEAKING out loud.

## Session Flow (Guided Freeform)
You have goals but no rigid script. Read the room and flow naturally:
1. OPEN with a DIRECT ROAST of one specific, niche purchase from their history. Pick the most interesting, embarrassing, or revealing item and call it out by name, brand, and price. This is the hook — it proves you know them.
   - Good: "So... you spent $85 on a COS shirt in November. Bold move for someone who also owns 4 Uniqlo basics."
   - Good: "Three ASOS orders in one week? That's not shopping, that's a lifestyle."
   - Pick something SPECIFIC and RECENT. Never be vague. The more niche the better.
2. ANALYZE their current outfit via the camera — compare it to their purchase history. Reference specific items they own: "Is that the $45 H&M hoodie? I recognize my enemies."
3. RECOMMEND items one at a time. Tie every recommendation back to something in their purchase history — what pairs with it, what upgrades it, what replaces it. "You clearly love basics — but THIS basic actually fits."
4. REACT to feedback — when they dislike something, reference their past choices: "You spent $120 on a Nike hoodie but THIS is where you draw the line?"
5. CLOSE with a genuine confidence boost, callback to their purchase history, and tell them to check their phone for links. "Your closet went from a 6 to an 8 today. We'll get you to a 10 next time."

## Tool Usage
- When you need to search for clothing, use the search_clothing tool. Craft specific queries informed by the user's style and the conversation.
- When you need to look something up in the user's email, use the search_gmail tool.
- When calling a tool, ALWAYS say something first like "Let me find something for you..." or "Ooh I have an idea, hold on" — never go silent during a tool call.
- Tool results are also sent directly to the UI, so the user will see the product card while you talk about it.

## Important Rules
- NEVER mention that you're an AI, an LLM, or Claude. You are Mira. Period.
- NEVER use emojis or special characters — this is spoken voice output.
- NEVER give long monologues. Keep it punchy. This is a 2-3 minute session.
- When presenting a clothing item, mention the item name, the price, and one compelling reason the user would like it. That's it.
- When the user likes an item (thumbs up), briefly acknowledge it and move on. Don't over-sell.
- Stay within the user's price range (~1.5x their average purchase price). Don't show $500 items to someone who shops at H&M.
"""


# Brands that are clearly not fashion retailers
_NON_FASHION_BRANDS = {
    "github", "google", "robinhood", "supabase", "medium", "reddit",
    "mail", "info", "news", "us", "gmail", "luma-mail", "united",
    "starbucks", "uber", "lyft", "doordash", "grubhub", "venmo",
    "paypal", "cashapp", "wise", "stripe", "anthropic", "openai",
    "vercel", "netlify", "heroku", "aws", "azure", "lovable",
    "bakedbymelissa", "slack", "notion", "figma", "linear",
}


def _filter_fashion_purchases(purchases: list[dict]) -> list[dict]:
    """Filter purchases to likely fashion/clothing items, removing junk."""
    filtered = []
    for p in purchases:
        brand = (p.get("brand") or "").strip()
        item_name = (p.get("item_name") or "").strip()

        # Skip non-fashion brands
        if brand.lower() in _NON_FASHION_BRANDS:
            continue

        # Skip items with HTML in the name (broken scraper output)
        if "<" in item_name or ">" in item_name:
            continue

        # Skip items with very long names (likely raw email body fragments)
        if len(item_name) > 120:
            continue

        # Skip items that look like notifications, not purchases
        skip_patterns = (
            "account confirmation", "security", "log in", "password",
            "oauth", "third-party", "background check", "attendance",
            "offer confirmation", "meeting records", "form:",
        )
        if any(pat in item_name.lower() for pat in skip_patterns):
            continue

        filtered.append(p)
    return filtered


def _format_purchase_stats(stats: dict) -> str:
    """Format aggregate purchase statistics for the system prompt."""
    if not stats or stats.get("total_count", 0) == 0:
        return ""

    lines = ["## Purchase Overview (Full History)"]
    lines.append(
        f"Total: {stats['total_count']} items, ${stats['total_spend']:.0f} spent "
        f"(avg ${stats['avg_price']:.0f}, range ${stats['min_price']:.0f}-${stats['max_price']:.0f})"
    )

    top_brands = stats.get("top_brands", [])
    if top_brands:
        brand_parts = [f"{b['brand']} ({b['count']}x, ${b['spend']:.0f})" for b in top_brands]
        lines.append(f"Top brands: {', '.join(brand_parts)}")

    categories = stats.get("categories", [])
    if categories:
        cat_parts = [f"{c['category']} ({c['count']})" for c in categories]
        lines.append(f"Categories: {', '.join(cat_parts)}")

    trend = stats.get("monthly_trend", [])
    if trend:
        trend_parts = [f"{t['month']}: {t['count']} items, ${t['spend']:.0f}" for t in trend]
        lines.append(f"Monthly trend: {' | '.join(trend_parts)}")

    return "\n".join(lines)


def _build_tiered_purchases(filtered_purchases: list[dict]) -> str:
    """Build a tiered display of purchases — recent at full detail, older compressed.

    Tiers:
    - Recent (last 30 days): Full detail — brand, item, price, date, category. Cap 25.
    - Older (30-90 days): Compact — brand + item + price. Cap 30.
    - Historical (90+ days): Brand counts only — "Nike x4, Zara x3".
    """
    now = datetime.now().date()
    thirty_days_ago = now - timedelta(days=30)
    ninety_days_ago = now - timedelta(days=90)

    recent, older, historical = [], [], []
    for p in filtered_purchases:
        date_str = p.get("date")
        if date_str:
            try:
                purchase_date = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
            except ValueError:
                purchase_date = None
        else:
            purchase_date = None

        if purchase_date and purchase_date >= thirty_days_ago:
            recent.append(p)
        elif purchase_date and purchase_date >= ninety_days_ago:
            older.append(p)
        else:
            historical.append(p)

    lines = []

    # Tier 1: Recent — full detail
    if recent:
        lines.append("### Recent Purchases (last 30 days)")
        for p in recent[:25]:
            price_str = f" (${p['price']})" if p.get("price") else ""
            date_str = f" on {p['date']}" if p.get("date") else ""
            cat_str = f" [{p['category']}]" if p.get("category") else ""
            lines.append(f"- {p.get('brand', '?')}: {p.get('item_name', '?')}{price_str}{date_str}{cat_str}")

    # Tier 2: Older — compact
    if older:
        lines.append("### Older Purchases (30-90 days)")
        for p in older[:30]:
            price_str = f" ${p['price']}" if p.get("price") else ""
            lines.append(f"- {p.get('brand', '?')} — {p.get('item_name', '?')}{price_str}")

    # Tier 3: Historical — brand counts only
    if historical:
        brand_counts = Counter(p.get("brand", "Unknown") for p in historical)
        brand_parts = [f"{brand} x{count}" for brand, count in brand_counts.most_common()]
        lines.append(f"### Historical Purchases (90+ days): {', '.join(brand_parts)}")

    if not lines:
        return ""

    lines.append(
        "\nNote: Use the search_purchases tool to look up specific items, brands, or date ranges "
        "from the user's full purchase archive."
    )

    return "\n".join(lines)


def build_system_prompt(
    user_profile: dict,
    purchases: list[dict],
    purchase_stats: dict | None = None,
    session_history: list[dict] | None = None,
    session_state: dict | None = None,
) -> str:
    """Build the full system prompt with user data injected."""
    parts = [MIRA_PERSONALITY]

    # User profile
    parts.append("\n## User Profile")
    name = user_profile.get("name", "this person")
    parts.append(f"Name: {name}")

    brands = user_profile.get("brands", [])
    if brands:
        parts.append(f"Favorite brands: {', '.join(brands)}")

    price_range = user_profile.get("price_range")
    if price_range:
        parts.append(
            f"Price range: ${price_range.get('min', '?')}-${price_range.get('max', '?')} "
            f"(avg ${price_range.get('avg', '?')})"
        )

    style_tags = user_profile.get("style_tags", [])
    if style_tags:
        parts.append(f"Style: {', '.join(style_tags)}")

    narrative = user_profile.get("narrative_summary")
    if narrative:
        parts.append(f"Style narrative: {narrative}")

    # Purchase statistics (aggregate view of full history)
    if purchase_stats:
        stats_section = _format_purchase_stats(purchase_stats)
        if stats_section:
            parts.append(f"\n{stats_section}")

    # Tiered purchases — filtered to fashion items, then displayed by recency
    filtered_purchases = _filter_fashion_purchases(purchases)
    if filtered_purchases:
        tiered = _build_tiered_purchases(filtered_purchases)
        if tiered:
            parts.append(f"\n## Purchase History (Tiered)")
            parts.append(tiered)
        else:
            parts.append("\n## Purchase History")
            parts.append("Purchases exist but could not be categorized by date.")
    else:
        parts.append("\n## Purchase History")
        parts.append(
            "No purchase history available. Skip the purchase roast — instead, "
            "open by commenting on what you can see (their outfit, their vibe) "
            "and ask about their style preferences directly."
        )

    # Past session memory
    if session_history:
        parts.append("\n## Past Sessions")
        for session in session_history[-3:]:  # Last 3 sessions
            parts.append(f"- {session.get('summary', 'No summary')}")
            liked = session.get("liked_items", [])
            if liked:
                names = [item.get("title", "?") for item in liked[:3]]
                parts.append(f"  Liked: {', '.join(names)}")

    # Current session state
    if session_state:
        parts.append("\n## Current Session")
        items_shown = session_state.get("items_shown", 0)
        likes = session_state.get("likes", 0)
        dislikes = session_state.get("dislikes", 0)
        api_calls = session_state.get("api_calls", 0)
        parts.append(f"Items shown: {items_shown}, Likes: {likes}, Dislikes: {dislikes}")
        if api_calls >= 18:
            parts.append("NOTE: You're approaching the session limit. Start wrapping up naturally — give a confidence boost and recap favorites.")

    return "\n".join(parts)
