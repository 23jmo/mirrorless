"""Serper.dev Shopping API search - CLI prototype for clothing data."""

import argparse
import os
import re
import sys

import httpx
from dotenv import load_dotenv

SERPER_SHOPPING_URL = "https://google.serper.dev/shopping"


def parse_price(price_str: str) -> float | None:
    """Extract numeric price from string like '$595.00' or '$1,299.99'."""
    match = re.search(r"[\d,]+\.?\d*", price_str.replace(",", ""))
    return float(match.group()) if match else None


def search_clothing(query: str, api_key: str, num_results: int = 10) -> list[dict]:
    """Search Serper.dev Shopping API and return structured results."""
    response = httpx.post(
        SERPER_SHOPPING_URL,
        headers={
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        },
        json={"q": query, "num": num_results},
    )
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("shopping", []):
        results.append({
            "title": item["title"],
            "source": item["source"],
            "price": item["price"],
            "price_numeric": parse_price(item["price"]),
            "image_url": item["imageUrl"],
            "link": item["link"],
            "product_id": item["productId"],
            "rating": item.get("rating"),
            "rating_count": item.get("ratingCount"),
        })

    return results


def print_results(results: list[dict], query: str) -> None:
    """Pretty-print search results to terminal."""
    print(f"\n{'='*70}")
    print(f"  Shopping results for: \"{query}\"")
    print(f"  {len(results)} items found")
    print(f"{'='*70}\n")

    for i, item in enumerate(results, 1):
        rating_str = f"{item['rating']}/5 ({item['rating_count']} reviews)" if item["rating"] else "No rating"
        print(f"  {i}. {item['title']}")
        print(f"     Seller:  {item['source']}")
        print(f"     Price:   {item['price']}")
        print(f"     Rating:  {rating_str}")
        print(f"     Image:   {item['image_url'][:80]}...")
        print(f"     Link:    {item['link'][:80]}...")
        print()


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Search clothing via Serper.dev Shopping API")
    parser.add_argument("query", help="Search query (e.g., 'mens leather jacket')")
    parser.add_argument("-n", "--num", type=int, default=10, help="Number of results (default: 10)")
    args = parser.parse_args()

    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        print("Error: SERPER_API_KEY not set. Add it to .env or export it.", file=sys.stderr)
        sys.exit(1)

    results = search_clothing(args.query, api_key, args.num)
    print_results(results, args.query)


if __name__ == "__main__":
    main()
