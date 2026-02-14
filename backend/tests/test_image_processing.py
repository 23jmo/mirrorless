"""Tests for image background removal service."""
import pytest
from services.image_processing import remove_background_from_url


def test_remove_background_returns_bytes():
    """Test that remove_background returns PNG bytes from a small test image."""
    # Use a small public domain image
    test_url = "https://via.placeholder.com/100x100/ff0000/ffffff.png"
    result = remove_background_from_url(test_url)
    assert isinstance(result, bytes)
    # PNG magic bytes
    assert result[:4] == b"\x89PNG"


def test_remove_background_invalid_url():
    """Test that invalid URL raises an error."""
    with pytest.raises(Exception):
        remove_background_from_url("https://invalid.example.com/nonexistent.png")
