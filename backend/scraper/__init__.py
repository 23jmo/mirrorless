"""Gmail scraping pipeline for purchase history extraction."""

from scraper.pipeline import fast_scrape, deep_scrape, ScrapeResult

__all__ = ["fast_scrape", "deep_scrape", "ScrapeResult"]
