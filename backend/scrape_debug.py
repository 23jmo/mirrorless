#!/usr/bin/env python3
"""Live Gmail scraper debug tool.

Re-scrapes your inbox in real-time and prints every step to the terminal.
Does NOT write anything to the database — purely read + display.

Usage:
    python scrape_debug.py <user_id>
    python scrape_debug.py <user_id> --no-llm
    python scrape_debug.py <user_id> --max-per-query 50
"""

import argparse
import asyncio
import json
import os
import sys
import textwrap

from dotenv import load_dotenv

load_dotenv()

# Import from existing scraper modules — no logic duplication
from agent.prompts import _NON_FASHION_BRANDS
from scraper.gmail_auth import build_gmail_service
from scraper.gmail_fetch import search_emails, get_message_content
from scraper.purchase_parser import (
    RECEIPT_SENDERS,
    _categorize_item,
    _detect_brand,
    _detect_merchant,
    _extract_order_status,
    _extract_tracking,
    _extract_with_llm,
    _is_receipt,
)
from scraper.pipeline import RECEIPT_QUERIES
from scraper.profile_builder import build_style_profile
from scraper.db import get_user_token
from models.database import NeonHTTPClient

try:
    from tabulate import tabulate
except ImportError:
    print("Missing dependency: pip install tabulate")
    sys.exit(1)


RECEIPT_KEYWORDS = ["order", "receipt", "confirmation", "shipped", "purchase"]

# LLM prompt template (matches purchase_parser._extract_with_llm exactly)
LLM_PROMPT_TEMPLATE = (
    'Extract clothing, shoes, and fashion accessory purchases from this receipt email. '
    'ONLY include fashion-related items (clothing, shoes, bags, jewelry, accessories). '
    'IGNORE non-fashion items like food, drinks, flowers, electronics, software, '
    'financial transactions, subscriptions.\n\n'
    'Return a JSON object with a single key "items" containing an array. '
    'Each item should have: brand (string), merchant (string or null), '
    'item_name (string), price (number or null), currency (string, default "USD"), '
    'order_status (string or null: confirmed/shipped/delivered).\n\n'
    'If this is not a fashion receipt or no fashion items can be extracted, '
    'return {"items": []}.\n\n'
    'Subject: {subject}\n\nBody:\n{body}'
)


def header(text: str) -> None:
    """Print a bold section header."""
    width = max(len(text) + 4, 60)
    print(f"\n{'=' * width}")
    print(f"  {text}")
    print(f"{'=' * width}\n")


def subheader(text: str) -> None:
    """Print a sub-section header."""
    print(f"\n--- {text} ---\n")


def _receipt_filter_reason(email: dict) -> tuple[bool, str]:
    """Explain why an email passed or failed the receipt filter."""
    sender = email.get("sender", "").lower()
    subject = email.get("subject", "").lower()

    sender_match = any(pattern in sender for pattern in RECEIPT_SENDERS)
    kw_matches = [kw for kw in RECEIPT_KEYWORDS if kw in subject]

    parts = []
    parts.append(f"sender={'YES' if sender_match else 'NONE'}")
    if kw_matches:
        parts.append(f"kw={','.join(kw_matches)}")
    else:
        parts.append("kw=NONE")

    is_receipt = sender_match or bool(kw_matches)
    return is_receipt, " ".join(parts)


def _truncate(text: str, length: int = 50) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ""
    return text[:length] + ("..." if len(text) > length else "")


# ── Step 1: Gmail Search ─────────────────────────────────────────────────────

def step1_search_gmail(service, queries: list[str], max_per_query: int) -> list[str]:
    """Search Gmail with each query, print results, return unique message IDs."""
    header("Step 1: Gmail Search (live API calls)")

    all_ids: list[str] = []
    seen = set()

    for query in queries:
        ids = search_emails(service, query=query, max_results=max_per_query)
        new_ids = [mid for mid in ids if mid not in seen]
        seen.update(ids)
        all_ids.extend(new_ids)

        new_label = f" ({len(new_ids)} new)" if len(new_ids) < len(ids) else ""
        print(f'  {query:<65} -> {len(ids)} emails found{new_label}')

    print(f"\nTotal: {len(all_ids)} unique emails. Fetching content...\n")
    return list(all_ids)


# ── Step 2: Fetch & Filter ────────────────────────────────────────────────────

def step2_fetch_and_filter(service, message_ids: list[str]) -> tuple[list[dict], list[dict]]:
    """Fetch each email, run receipt filter, print table. Returns (all_emails, receipt_emails)."""
    header("Step 2: Receipt Filter Results")

    all_emails = []
    receipt_emails = []
    table_rows = []

    no_sender = 0
    no_kw = 0
    no_both = 0

    for i, msg_id in enumerate(message_ids, 1):
        try:
            email = get_message_content(service, msg_id)
        except Exception as e:
            print(f"  [!] Failed to fetch message {msg_id}: {e}")
            continue

        all_emails.append(email)
        is_receipt, reason = _receipt_filter_reason(email)

        if is_receipt:
            receipt_emails.append(email)

        # Track rejection reasons
        if not is_receipt:
            sender_ok = "sender=YES" in reason or "sender=NONE" not in reason
            kw_ok = "kw=NONE" not in reason
            if not sender_ok and not kw_ok:
                no_both += 1
            elif not sender_ok:
                no_sender += 1
            else:
                no_kw += 1

        table_rows.append([
            i,
            _truncate(email.get("subject", ""), 40),
            _truncate(email.get("sender", ""), 30),
            "YES" if is_receipt else "NO",
            reason,
        ])

    print(tabulate(
        table_rows,
        headers=["#", "Subject", "Sender", "Receipt?", "Why"],
        tablefmt="pipe",
    ))

    passed = len(receipt_emails)
    rejected = len(all_emails) - passed
    reject_detail = f"{no_sender} no sender match, {no_kw} no subject kw, {no_both} neither"
    print(f"\nPassed: {passed} / Rejected: {rejected} ({reject_detail})\n")

    return all_emails, receipt_emails


# ── Step 3: Extraction ────────────────────────────────────────────────────────

def step3_extract(receipt_emails: list[dict], no_llm: bool) -> list[dict]:
    """Run LLM extraction on each receipt email with full debug output."""
    header("Step 3: Extraction — LLM-only (per email)")

    # Check auth token availability
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    if not auth_token and not no_llm:
        print("!! WARNING: ANTHROPIC_AUTH_TOKEN is not set.")
        print("!! All LLM calls will silently return empty results.")
        print("!! Set the token in .env or run with --no-llm to skip LLM calls.\n")

    # Print the LLM prompt template once
    print("LLM PROMPT TEMPLATE (printed once):")
    for line in LLM_PROMPT_TEMPLATE.split("\n"):
        print(f"  {line}")
    print()

    all_items = []
    method_counts = {"llm": 0, "brand-filtered": 0, "skipped": 0, "none": 0}

    for i, email in enumerate(receipt_emails, 1):
        subheader(f"Email {i}/{len(receipt_emails)}")

        subject = email.get("subject", "")
        sender = email.get("sender", "")
        body = email.get("body", "")
        full_text = f"{subject}\n{body}"

        print(f"  Subject: {subject}")
        print(f"  Sender:  {sender}")
        body_preview = body.replace("\n", " ")[:120]
        print(f'  Body:    "{body_preview}..."')
        print()

        brand = _detect_brand(full_text, sender)
        merchant = _detect_merchant(sender)

        print(f"  Brand: {brand}  |  Merchant: {merchant or '(none)'}")

        # Brand filter check
        if brand.lower() in _NON_FASHION_BRANDS or (merchant or "").lower() in _NON_FASHION_BRANDS:
            filtered_by = brand if brand.lower() in _NON_FASHION_BRANDS else merchant
            print(f"  >> SKIPPED by brand filter: \"{filtered_by}\" is non-fashion")
            print()
            method_counts["brand-filtered"] += 1
            continue

        order_status = _extract_order_status(full_text)
        tracking_number = _extract_tracking(full_text)
        receipt_text = full_text[:500] if full_text else None

        purchases = []

        if no_llm:
            print(f"  Method: LLM (skipped — --no-llm flag)")
            print(f"  Would send to Haiku:")
            print(f"    Subject: {subject}")
            print(f"    Body: {_truncate(body[:2000], 200)}")
            print()
            method_counts["skipped"] += 1
        else:
            print(f"  Method: LLM (sending to Claude Haiku)")
            print(f"  LLM input:")
            print(f"    Subject: {subject}")
            print(f"    Body: {_truncate(body[:2000], 200)}")
            print()

            llm_items = _extract_with_llm(email)

            if llm_items:
                print(f"  LLM response (full JSON):")
                print(textwrap.indent(json.dumps({"items": llm_items}, indent=2), "    "))
                print()
            else:
                print(f"  LLM response: no items extracted")
                print()

            for item in llm_items:
                item_name = item.get("item_name", "")
                if not item_name or len(item_name) < 3:
                    continue
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
                    "method": "llm",
                })

            method_counts["llm" if purchases else "none"] += 1

        if purchases:
            item_rows = []
            for j, p in enumerate(purchases, 1):
                price_str = f"${p['price']:.2f}" if p.get("price") is not None else "N/A"
                item_rows.append([
                    j,
                    _truncate(p["item_name"], 35),
                    _truncate(p.get("brand", ""), 15),
                    _truncate(p.get("merchant", "") or "", 15),
                    p.get("category") or "—",
                    price_str,
                ])
            print("  Extracted:")
            print(textwrap.indent(tabulate(
                item_rows,
                headers=["#", "item_name", "brand", "merchant", "category", "price"],
                tablefmt="pipe",
            ), "  "))
            print()

            all_items.extend(purchases)
        elif not no_llm:
            print("  Extracted: (nothing)\n")

    print(f"\nMethods: {method_counts.get('llm', 0)} llm, "
          f"{method_counts.get('brand-filtered', 0)} brand-filtered, "
          f"{method_counts.get('skipped', 0)} skipped (--no-llm), "
          f"{method_counts.get('none', 0)} no items")

    return all_items


# ── Step 4: Summary ──────────────────────────────────────────────────────────

def step4_summary(all_items: list[dict]) -> None:
    """Print final summary table and style profile."""
    header("Step 4: Summary")

    if not all_items:
        print("No items were extracted.")
        return

    summary_rows = []
    for i, item in enumerate(all_items, 1):
        price_str = f"${item['price']:.2f}" if item.get("price") is not None else "N/A"
        summary_rows.append([
            i,
            _truncate(item["item_name"], 30),
            _truncate(item.get("brand", ""), 12),
            _truncate(item.get("merchant", "") or "", 12),
            item.get("category") or "—",
            price_str,
            item.get("method", "?"),
        ])

    print(tabulate(
        summary_rows,
        headers=["#", "Item Name", "Brand", "Merchant", "Category", "Price", "Method"],
        tablefmt="pipe",
    ))

    # Build style profile
    print()
    subheader("Style Profile")
    # Brand frequency from subjects is skipped in this tool (would need a second Gmail pass)
    profile = build_style_profile(all_items, {})

    print(f"  Brands:    {', '.join(profile['brands'][:10]) or '(none)'}")
    pr = profile["price_range"]
    print(f"  Price:     ${pr['min']:.2f} – ${pr['max']:.2f} (avg ${pr['avg']:.2f})")
    print(f"  Tags:      {', '.join(profile['style_tags']) or '(none)'}")
    if profile.get("narrative_summary"):
        print(f"  Narrative: {profile['narrative_summary']}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

async def async_main(user_id: str, no_llm: bool, max_per_query: int) -> None:
    """Orchestrate the full debug scrape."""
    print(f"Scrape Debug Tool")
    print(f"User ID: {user_id}")
    print(f"Options: no_llm={no_llm}, max_per_query={max_per_query}")

    # Fetch OAuth token from Neon DB
    db = NeonHTTPClient()
    try:
        token_data = await get_user_token(db, user_id)
    finally:
        await db.close()

    if not token_data:
        print(f"\nError: No OAuth token found for user {user_id}.")
        print("The user must complete Google OAuth first (POST /auth/google).")
        sys.exit(1)

    print(f"OAuth token found (keys: {list(token_data.keys())})")

    # Build Gmail service
    service = build_gmail_service(token_data)
    print("Gmail API service built successfully.\n")

    # Step 1: Search
    message_ids = step1_search_gmail(service, RECEIPT_QUERIES, max_per_query)

    if not message_ids:
        print("No emails found. Check that the user has Gmail access.")
        return

    # Step 2: Fetch & Filter
    all_emails, receipt_emails = step2_fetch_and_filter(service, message_ids)

    if not receipt_emails:
        print("No receipt emails found after filtering.")
        return

    # Step 3: Extract
    all_items = step3_extract(receipt_emails, no_llm)

    # Step 4: Summary
    step4_summary(all_items)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Live Gmail scraper debug tool — re-scrapes and prints everything",
    )
    parser.add_argument("user_id", help="UUID of the user to scrape")
    parser.add_argument(
        "--no-llm", action="store_true",
        help="Skip Claude API calls (faster, free)",
    )
    parser.add_argument(
        "--max-per-query", type=int, default=20,
        help="Max emails to fetch per search query (default: 20)",
    )

    args = parser.parse_args()
    asyncio.run(async_main(args.user_id, args.no_llm, args.max_per_query))


if __name__ == "__main__":
    main()
