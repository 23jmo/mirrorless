"""Tests for brand frequency scanner."""

from scraper.brand_scanner import scan_brand_frequency


def test_scan_brand_frequency_counts_brands():
    """Counts brand mentions across email subjects."""
    subjects = [
        "Your Nike order has shipped",
        "Nike sale: 30% off everything",
        "Zara: Your order is confirmed",
        "Meeting at 3pm",
        "Aritzia new arrivals",
        "Nike Air Max restock alert",
    ]
    result = scan_brand_frequency(subjects)
    assert result["Nike"] == 3
    assert result["Zara"] == 1
    assert result["Aritzia"] == 1
    assert "Meeting" not in result


def test_scan_brand_frequency_empty():
    """Empty input returns empty dict."""
    assert scan_brand_frequency([]) == {}


def test_scan_brand_frequency_sorted_by_count():
    """Results are sorted by frequency descending."""
    subjects = ["Zara order"] * 5 + ["Nike order"] * 3 + ["H&M sale"] * 1
    result = scan_brand_frequency(subjects)
    brands = list(result.keys())
    assert brands[0] == "Zara"
    assert brands[1] == "Nike"
