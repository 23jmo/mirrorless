"""Scan email subject lines for brand frequency."""

from collections import Counter
from scraper.purchase_parser import KNOWN_BRANDS


def scan_brand_frequency(subjects: list[str]) -> dict[str, int]:
    """Count how often known brands appear in a list of email subjects.

    Returns dict of {brand: count}, sorted by count descending.
    Only includes brands with at least 1 match.
    """
    counts: Counter = Counter()
    for subject in subjects:
        subject_lower = subject.lower()
        for brand in KNOWN_BRANDS:
            if brand.lower() in subject_lower:
                counts[brand] += 1
    return dict(counts.most_common())
