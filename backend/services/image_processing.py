"""Background removal service using rembg."""

import io

import httpx
from PIL import Image
from rembg import remove


def remove_background_from_url(image_url: str) -> bytes:
    """Download image from URL and remove its background.

    Returns PNG bytes with transparent background.
    """
    response = httpx.get(image_url, timeout=30)
    response.raise_for_status()

    input_image = Image.open(io.BytesIO(response.content))
    output_image = remove(input_image)

    output_buffer = io.BytesIO()
    output_image.save(output_buffer, format="PNG")
    return output_buffer.getvalue()
