# Serper.dev Shopping Scraper Prototype

## Goal

Prove the Serper.dev Shopping API returns clean, structured clothing data suitable for Mirrorless's recommendation pipeline. CLI script that takes a search query and pretty-prints results.

## API Details

- Endpoint: `POST https://google.serper.dev/shopping`
- Auth: `X-API-KEY` header
- Returns 40 results per query, costs 1 credit each
- Rate limit: 5 req/s

### Fields (always present)

- `title`, `source`, `price` (string), `imageUrl`, `link`, `productId`, `position`

### Fields (optional, ~90% present)

- `rating` (float), `ratingCount` (int)

## Implementation

Single file: `backend/services/serper_search.py`

- Reads `SERPER_API_KEY` from env or `.env`
- Takes search query from CLI args
- Hits `/shopping` endpoint via `httpx`
- Parses price string to float
- Pretty-prints formatted table to stdout
- No new dependencies (httpx + python-dotenv already in requirements.txt)

## Future

Wire into FastAPI endpoint + feed results to Claude for outfit recommendations.
