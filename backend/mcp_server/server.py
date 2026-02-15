"""MCP server for Mirrorless — exposes shopping + mirror tools to Poke.

Run standalone:
    cd backend && python -m mcp_server.server

Or via uvicorn:
    cd backend && uvicorn mcp_server.server:app --host 0.0.0.0 --port 8001
"""

import logging
import os

from dotenv import load_dotenv
from fastmcp import FastMCP

from mcp_server.mirror import (
    do_get_past_sessions,
    do_present_items,
    do_save_session,
    do_send_to_mirror,
)
from mcp_server.shopping import search_serper

load_dotenv()

log = logging.getLogger("mcp")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

mcp = FastMCP(
    "Mirrorless Shopping",
    instructions="""You are connected to a smart mirror. These tools are the ONLY way
to search for clothes and show things on the user's physical mirror display.

MANDATORY: Whenever the user mentions ANYTHING related to shopping, clothing, fashion,
outfits, style, accessories, shoes, or getting dressed — you MUST use these tools.
Do NOT answer from your own knowledge about products. ALWAYS search with search_clothing
and show results on the mirror with present_items. The user is standing in front of a
mirror and expects to SEE items on it.

TOOLS:
- search_clothing: Search for clothing items online. Use detailed queries with
  gender, style keywords, occasion, price range. Returns results with images and prices.
  Results go to you ONLY — the user does NOT see them until you call present_items.

- present_items: Display 1-5 curated items on the user's smart mirror. REQUIRED after
  every search — this is how the user actually sees products. Each item needs:
  title, price, image_url, link, source.

- send_to_mirror: Send text to display on the mirror screen. Use this for commentary,
  styling advice, greetings, and reactions. The mirror speaks this text aloud via TTS.
  ALWAYS use this alongside present_items so the user hears your reasoning.

- get_past_sessions: Retrieve previous shopping sessions. Returns items shown, user
  reactions (liked/disliked/skipped), and summaries. Use this to personalize.

- save_session: Save a session summary when done. Include items shown and reactions.

WORKFLOW — follow this every time:
1. Get the user's mirror_id (permanent code like "MIRROR-A1") — ask if you don't have it
2. ALWAYS call get_past_sessions first to check history
3. Use send_to_mirror to greet them on the mirror
4. Search with search_clothing based on what you know about the user
5. Pick your best 1-5 results and call present_items to show them on the mirror
6. ALWAYS call send_to_mirror alongside present_items to explain your picks
7. React to feedback, refine searches, keep showing items on the mirror
8. When done, ALWAYS call save_session with a summary

RULES:
- NEVER skip search_clothing for shopping requests — always search live, never guess
- NEVER skip present_items after searching — the user expects to see items on their mirror
- NEVER skip send_to_mirror alongside present_items — always explain your picks
- ALWAYS call get_past_sessions at the start to build on previous interactions
- ALWAYS call save_session at the end so future sessions can reference this one
""",
)


@mcp.tool
async def search_clothing(query: str, num_results: int = 8) -> dict:
    """Search for clothing items using Google Shopping via Serper API.

    Returns product results with images, prices, and buy links. Results go to
    you only — the user does NOT see them. Use present_items to show curated
    picks on their mirror.

    Args:
        query: Detailed shopping search query with gender, style, and price hints.
               Example: "mens black minimalist sneakers under $150"
        num_results: Number of results to return (default 8, max 20).
    """
    log.info("search_clothing called | query=%r num_results=%d", query, num_results)
    result = await search_serper(query, num_results)
    count = len(result.get("results", []))
    if "error" in result:
        log.error("search_clothing error: %s", result["error"])
    else:
        log.info("search_clothing returned %d results", count)
    return result


@mcp.tool
async def present_items(mirror_id: str, items: list[dict]) -> dict:
    """Display 1-5 curated clothing items on the user's smart mirror.

    Call this AFTER search_clothing with your top picks. The user sees product
    cards (image + price + brand) on their physical mirror display.

    Args:
        mirror_id: The mirror's permanent ID (e.g. "MIRROR-A1").
        items: List of 1-5 items, each with: title, price, image_url, link, source.
    """
    titles = [item.get("title", "?") for item in items]
    log.info("present_items called | mirror=%s items=%d titles=%s", mirror_id, len(items), titles)
    result = await do_present_items(mirror_id, items)
    if "error" in result:
        log.error("present_items error: %s", result["error"])
    else:
        log.info("present_items success | mirror=%s", mirror_id)
    return result


@mcp.tool
async def send_to_mirror(mirror_id: str, text: str) -> dict:
    """Send text to display on the user's smart mirror screen.

    The mirror displays this text and can speak it aloud via TTS. Use this to
    show your commentary, styling advice, or reactions alongside product cards.

    Args:
        mirror_id: The mirror's permanent ID (e.g. "MIRROR-A1").
        text: The text to display and optionally speak on the mirror.
    """
    log.info("send_to_mirror called | mirror=%s text=%r", mirror_id, text[:100])
    result = await do_send_to_mirror(mirror_id, text)
    if "error" in result:
        log.error("send_to_mirror error: %s", result["error"])
    else:
        log.info("send_to_mirror success | mirror=%s", mirror_id)
    return result


@mcp.tool
async def get_past_sessions(mirror_id: str, limit: int = 5) -> dict:
    """Retrieve previous shopping sessions for this mirror.

    Returns session dates, items shown, user reactions (liked/disliked/skipped),
    and summaries. Use this to personalize recommendations by referencing what
    they liked or disliked before.

    Args:
        mirror_id: The mirror's permanent ID (e.g. "MIRROR-A1").
        limit: Max number of sessions to return (default 5).
    """
    log.info("get_past_sessions called | mirror=%s limit=%d", mirror_id, limit)
    result = await do_get_past_sessions(mirror_id, limit)
    if "error" in result:
        log.error("get_past_sessions error: %s", result["error"])
    else:
        session_count = len(result.get("sessions", []))
        log.info("get_past_sessions returned %d sessions | mirror=%s", session_count, mirror_id)
    return result


@mcp.tool
async def save_session(
    mirror_id: str,
    summary: str,
    items_shown: list[dict] | None = None,
    reactions: dict | None = None,
) -> dict:
    """Save a session summary when the shopping conversation ends.

    ALWAYS call this when wrapping up a shopping interaction so future sessions
    can reference what happened.

    Args:
        mirror_id: The mirror's permanent ID (e.g. "MIRROR-A1").
        summary: Brief recap of the session (e.g. "Looked at date night outfits, loved the navy blazer").
        items_shown: List of items that were shown, each optionally with a "reaction" field.
        reactions: Aggregate reaction counts (e.g. {"likes": 2, "dislikes": 1, "items_shown": 5}).
    """
    item_count = len(items_shown) if items_shown else 0
    log.info("save_session called | mirror=%s items=%d summary=%r", mirror_id, item_count, summary[:100])
    result = await do_save_session(mirror_id, summary, items_shown, reactions)
    if "error" in result:
        log.error("save_session error: %s", result["error"])
    else:
        log.info("save_session success | mirror=%s session_id=%s", mirror_id, result.get("session_id"))
    return result


# --- Entry point ---

app = mcp.http_app()

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("MCP_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
