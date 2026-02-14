"""CLI test harness for Mira agent — fast iteration without frontend.

Usage:
    python -m agent.test_harness --mock          # Mock user data (no DB needed)
    python -m agent.test_harness --user-id UUID   # Real DB user
    python -m agent.test_harness --mock --script tests/mira_script.txt

Interactive commands:
    /like, /dislike, /left, /right   — simulate gestures
    /snapshot                        — simulate camera snapshot (placeholder)
    /status                          — show session counters
    /end                             — end the session
    /quit                            — exit immediately
"""

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass, field

# Ensure backend root is on the path when run as a module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from agent.orchestrator import MiraOrchestrator, SessionState


# ── Mock data ────────────────────────────────────────────────────────────────

MOCK_USER_ID = "cli-mock-user-0001"

MOCK_PROFILE = {
    "user_id": MOCK_USER_ID,
    "name": "Jordan",
    "email": "jordan@test.com",
    "brands": ["Nike", "Zara", "Uniqlo", "ASOS", "COS"],
    "price_range": {"min": 15, "max": 150, "avg": 55},
    "style_tags": ["streetwear", "minimalist", "casual"],
    "narrative_summary": (
        "Streetwear core with a minimalist streak. Heavy Nike loyalty "
        "(shoes especially), fast-fashion fill-ins from Zara and ASOS. "
        "Gravitates toward monochrome and muted earth tones. "
        "Occasionally splurges on statement outerwear."
    ),
}

MOCK_PURCHASES = [
    {"brand": "Nike", "item_name": "Air Force 1 '07", "category": "shoes", "price": 115.0, "date": "2026-02-10"},
    {"brand": "Zara", "item_name": "Oversized Blazer", "category": "outerwear", "price": 89.99, "date": "2026-02-05"},
    {"brand": "COS", "item_name": "Minimalist Wool Shirt", "category": "tops", "price": 85.0, "date": "2026-01-30"},
    {"brand": "Uniqlo", "item_name": "Heattech Crew Neck T-Shirt", "category": "tops", "price": 14.90, "date": "2026-01-28"},
    {"brand": "ASOS", "item_name": "Slim Fit Chinos", "category": "bottoms", "price": 35.00, "date": "2026-01-10"},
    {"brand": "Nike", "item_name": "Tech Fleece Joggers", "category": "bottoms", "price": 110.0, "date": "2025-12-15"},
    {"brand": "Zara", "item_name": "Minimalist Leather Belt", "category": "accessories", "price": 29.90, "date": "2025-12-01"},
    {"brand": "ASOS", "item_name": "Oversized Hoodie", "category": "tops", "price": 42.00, "date": "2025-11-28"},
    {"brand": "ASOS", "item_name": "Relaxed Fit Cargo Pants", "category": "bottoms", "price": 48.00, "date": "2025-11-25"},
    {"brand": "ASOS", "item_name": "Cropped Puffer Jacket", "category": "outerwear", "price": 72.00, "date": "2025-11-20"},
    {"brand": "Nike", "item_name": "Dunk Low Retro", "category": "shoes", "price": 110.0, "date": "2025-11-15"},
    {"brand": "Uniqlo", "item_name": "Stretch Selvedge Jeans", "category": "bottoms", "price": 49.90, "date": "2025-10-20"},
    {"brand": "COS", "item_name": "Merino Cardigan", "category": "tops", "price": 99.0, "date": "2025-10-01"},
]

MOCK_PAST_SESSIONS = [
    {
        "summary": "Jordan liked a Zara bomber jacket and Nike Blazers. Vibed with monochrome looks. Passed on anything too colorful.",
        "liked_items": [
            {"title": "Zara Bomber Jacket", "price": "$79.90"},
            {"title": "Nike Blazer Mid '77", "price": "$105.00"},
        ],
    },
]

MOCK_PURCHASE_STATS = {
    "total_count": 13,
    "total_spend": 900.69,
    "avg_price": 69.28,
    "min_price": 14.90,
    "max_price": 115.0,
    "top_brands": [
        {"brand": "Nike", "count": 3, "spend": 335.0},
        {"brand": "ASOS", "count": 4, "spend": 197.0},
        {"brand": "Zara", "count": 2, "spend": 119.89},
        {"brand": "COS", "count": 2, "spend": 184.0},
        {"brand": "Uniqlo", "count": 2, "spend": 64.80},
    ],
    "categories": [
        {"category": "bottoms", "count": 4, "spend": 242.9},
        {"category": "tops", "count": 4, "spend": 240.9},
        {"category": "shoes", "count": 3, "spend": 335.0},
        {"category": "outerwear", "count": 2, "spend": 161.99},
    ],
    "monthly_trend": [
        {"month": "2026-02", "count": 2, "spend": 204.99},
        {"month": "2026-01", "count": 3, "spend": 134.9},
        {"month": "2025-12", "count": 2, "spend": 139.9},
        {"month": "2025-11", "count": 4, "spend": 272.0},
    ],
}


# ── CLI Socket Mock ──────────────────────────────────────────────────────────

class CLISocketMock:
    """Mock Socket.io that prints events to the terminal."""

    async def emit(self, event: str, data: dict, room: str = "") -> None:
        if event == "mira_speech":
            # Print speech chunks inline (no newline, streams naturally)
            text = data.get("text", "")
            print(text, end="", flush=True)
        elif event == "tool_result":
            items = data.get("items", [])
            print(f"\n\033[36m[MIRROR DISPLAY] Showing {len(items)} item(s):\033[0m")
            for i, item in enumerate(items, 1):
                price = item.get("price", "?")
                title = item.get("title", "?")
                source = item.get("source", "?")
                print(f"  \033[36m{i}. {title} — {price} ({source})\033[0m")
        elif event == "session_ended":
            summary = data.get("summary", "")
            stats = data.get("stats", {})
            print(f"\n\033[33m[SESSION ENDED]\033[0m")
            print(f"  Summary: {summary}")
            print(f"  Stats: {json.dumps(stats)}")
        elif event == "request_snapshot":
            print("\n\033[35m[SNAPSHOT REQUESTED] (simulated — no camera in CLI)\033[0m")
        elif event == "debug_system_prompt":
            # Suppress in CLI — too verbose
            pass
        else:
            print(f"\n\033[90m[socket:{event}] {json.dumps(data, default=str)[:200]}\033[0m")


# ── Mock Orchestrator (bypasses DB) ──────────────────────────────────────────

class MockMiraOrchestrator(MiraOrchestrator):
    """Orchestrator that uses mock data instead of the database."""

    async def start_session(self, user_id: str) -> SessionState:
        """Initialize session with mock data — no DB calls."""
        if user_id in self.sessions:
            await self.end_session(user_id)

        session = SessionState(user_id=user_id)
        self.sessions[user_id] = session

        session.user_context = {
            "profile": MOCK_PROFILE,
            "purchases": MOCK_PURCHASES,
            "past_sessions": MOCK_PAST_SESSIONS,
            "oauth_token": None,
            "purchase_stats": MOCK_PURCHASE_STATS,
        }

        from agent.prompts import build_system_prompt

        session.system_prompt = build_system_prompt(
            user_profile=MOCK_PROFILE,
            purchases=MOCK_PURCHASES,
            purchase_stats=MOCK_PURCHASE_STATS,
            session_history=MOCK_PAST_SESSIONS,
            session_state={"items_shown": 0, "likes": 0, "dislikes": 0, "api_calls": 0},
        )

        # Skip DB insert, skip silence timer (CLI is interactive)

        # Trigger Mira's opening line
        await self.handle_event(user_id, {
            "type": "session_start",
            "message": "A new user just stepped up to the mirror. Introduce yourself and start the session.",
        })

        return session

    async def end_session(self, user_id: str) -> dict | None:
        """End session without DB save."""
        session = self.sessions.get(user_id)
        if not session:
            return None

        session.is_active = False
        self._cancel_silence_timer(user_id)

        try:
            summary = await self._generate_summary(session)
        except Exception as e:
            print(f"\n[harness] Summary generation failed: {e}")
            summary = "Session ended."

        if self.sio:
            await self.sio.emit(
                "session_ended",
                {
                    "session_id": session.session_id,
                    "summary": summary,
                    "liked_items": session.liked_items,
                    "stats": {
                        "items_shown": session.items_shown,
                        "likes": session.likes,
                        "dislikes": session.dislikes,
                    },
                },
                room=user_id,
            )

        del self.sessions[user_id]
        return {"summary": summary, "liked_items": session.liked_items}


# ── Gesture / Command Mapping ────────────────────────────────────────────────

GESTURE_SHORTCUTS = {
    "/like": {"type": "gesture", "gesture": "thumbs_up"},
    "/dislike": {"type": "gesture", "gesture": "thumbs_down"},
    "/right": {"type": "gesture", "gesture": "swipe_right"},
    "/left": {"type": "gesture", "gesture": "swipe_left"},
    "/snapshot": {"type": "snapshot", "image_base64": ""},  # placeholder
}


# ── Main Loop ────────────────────────────────────────────────────────────────

async def run_interactive(orchestrator: MiraOrchestrator, user_id: str) -> None:
    """Run an interactive CLI session with Mira."""
    print("\n\033[1m╔══════════════════════════════════════════╗\033[0m")
    print("\033[1m║       MIRA CLI TEST HARNESS              ║\033[0m")
    print("\033[1m╠══════════════════════════════════════════╣\033[0m")
    print("\033[1m║\033[0m  Commands:                               \033[1m║\033[0m")
    print("\033[1m║\033[0m    /like /dislike /left /right            \033[1m║\033[0m")
    print("\033[1m║\033[0m    /snapshot /status /end /quit           \033[1m║\033[0m")
    print("\033[1m║\033[0m  Or type a message to speak to Mira      \033[1m║\033[0m")
    print("\033[1m╚══════════════════════════════════════════╝\033[0m\n")

    print("[harness] Starting session...\n")
    print("\033[1mMira:\033[0m ", end="", flush=True)
    await orchestrator.start_session(user_id)
    print()  # newline after streamed opener

    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("\n\033[1mYou:\033[0m ")
            )
        except (EOFError, KeyboardInterrupt):
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input == "/quit":
            break

        if user_input == "/end":
            print("\n[harness] Ending session...")
            await orchestrator.end_session(user_id)
            break

        if user_input == "/status":
            session = orchestrator.sessions.get(user_id)
            if session:
                print(f"\n\033[33m[STATUS]\033[0m")
                print(f"  API calls: {session.api_calls}")
                print(f"  Items shown: {session.items_shown}")
                print(f"  Likes: {session.likes} | Dislikes: {session.dislikes}")
                print(f"  Liked items: {len(session.liked_items)}")
                print(f"  History length: {len(session.conversation_history)} messages")
            continue

        # Check for gesture shortcuts
        if user_input in GESTURE_SHORTCUTS:
            event = GESTURE_SHORTCUTS[user_input]
            print(f"\n\033[35m[GESTURE: {event.get('gesture', event.get('type'))}]\033[0m")
        else:
            event = {"type": "voice", "transcript": user_input}

        print("\n\033[1mMira:\033[0m ", end="", flush=True)
        await orchestrator.handle_event(user_id, event)
        print()  # newline after streamed response


async def run_script(orchestrator: MiraOrchestrator, user_id: str, script_path: str) -> None:
    """Run a scripted session from a file."""
    with open(script_path) as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"[harness] Running script: {script_path} ({len(lines)} lines)\n")
    print("\033[1mMira:\033[0m ", end="", flush=True)
    await orchestrator.start_session(user_id)
    print()

    for line in lines:
        print(f"\n\033[1mScript:\033[0m {line}")

        if line == "/end":
            await orchestrator.end_session(user_id)
            break

        if line in GESTURE_SHORTCUTS:
            event = GESTURE_SHORTCUTS[line]
        else:
            event = {"type": "voice", "transcript": line}

        print("\n\033[1mMira:\033[0m ", end="", flush=True)
        await orchestrator.handle_event(user_id, event)
        print()

    print("\n[harness] Script complete.")


def main():
    parser = argparse.ArgumentParser(description="Mira CLI Test Harness")
    parser.add_argument("--mock", action="store_true", help="Use mock user data (no DB)")
    parser.add_argument("--user-id", type=str, help="Real user ID from database")
    parser.add_argument("--script", type=str, help="Path to script file for automated testing")
    args = parser.parse_args()

    if not args.mock and not args.user_id:
        parser.error("Must specify either --mock or --user-id")

    cli_socket = CLISocketMock()

    if args.mock:
        orchestrator = MockMiraOrchestrator(socket_io=cli_socket)
        user_id = MOCK_USER_ID
    else:
        orchestrator = MiraOrchestrator(socket_io=cli_socket)
        user_id = args.user_id

    if args.script:
        asyncio.run(run_script(orchestrator, user_id, args.script))
    else:
        asyncio.run(run_interactive(orchestrator, user_id))


if __name__ == "__main__":
    main()
