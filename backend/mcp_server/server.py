"""MCP server for Mirrorless — exposes shopping + mirror tools to Poke.

Run standalone:
    cd backend && python -m mcp_server.server

Or via uvicorn:
    cd backend && uvicorn mcp_server.server:app --host 0.0.0.0 --port 8001
"""

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

mcp = FastMCP(
    "Mirrorless Shopping",
    instructions="""Personal shopping assistant tools for a smart mirror display.

TOOLS:
- search_clothing: Search for clothing items online. Use detailed queries including
  gender, style keywords, occasion, and price range. Returns product results with
  images and prices. Example: "womens oversized cream wool coat under $200"

- present_items: Display 1-5 curated clothing items on the user's smart mirror.
  Requires mirror_id. Each item needs: title, price, image_url, link, source.

- send_to_mirror: Send text to display on the user's smart mirror screen.
  Use this to show your commentary, styling advice, or reactions on the mirror.
  The mirror can also speak this text aloud via text-to-speech.
  Requires mirror_id.

- get_past_sessions: Retrieve previous shopping sessions for this mirror.
  Returns session dates, items shown, user reactions (liked/disliked/skipped),
  and summaries. Use this to personalize recommendations — reference items they
  liked or disliked in past sessions.

- save_session: Save a session summary when the shopping conversation ends.
  Include items shown, reactions, and a brief summary of what happened.
  ALWAYS call this when wrapping up a shopping interaction.

WORKFLOW:
1. Get the user's mirror_id if you don't have it yet (the code on their mirror)
2. Call get_past_sessions to check their history — reference past likes/dislikes
3. Use send_to_mirror to greet them on the mirror
4. Search for items based on what you know about the user + their session history
5. Pick your best 1-5 results and display them via present_items
6. Use send_to_mirror to explain why you chose those items
7. React to feedback, refine, and keep the conversation going on the mirror
8. When done, call save_session with a summary of what happened

IMPORTANT:
- ALWAYS use send_to_mirror alongside present_items so the user sees your
  commentary on the mirror, not just in their phone.
- ALWAYS call get_past_sessions at the start to build on previous interactions.
- ALWAYS call save_session at the end so future sessions can reference this one.
- The user's purchase history, calendar, and preferences are available to you
  through your own integrations — use that context to personalize everything.
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
    return await search_serper(query, num_results)


@mcp.tool
async def present_items(mirror_id: str, items: list[dict]) -> dict:
    """Display 1-5 curated clothing items on the user's smart mirror.

    Call this AFTER search_clothing with your top picks. The user sees product
    cards (image + price + brand) on their physical mirror display.

    Args:
        mirror_id: The mirror's permanent ID (e.g. "MIRROR-A1").
        items: List of 1-5 items, each with: title, price, image_url, link, source.
    """
    return await do_present_items(mirror_id, items)


@mcp.tool
async def send_to_mirror(mirror_id: str, text: str) -> dict:
    """Send text to display on the user's smart mirror screen.

    The mirror displays this text and can speak it aloud via TTS. Use this to
    show your commentary, styling advice, or reactions alongside product cards.

    Args:
        mirror_id: The mirror's permanent ID (e.g. "MIRROR-A1").
        text: The text to display and optionally speak on the mirror.
    """
    return await do_send_to_mirror(mirror_id, text)


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
    return await do_get_past_sessions(mirror_id, limit)


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
    return await do_save_session(mirror_id, summary, items_shown, reactions)


# --- Entry point ---

app = mcp.http_app()

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("MCP_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
