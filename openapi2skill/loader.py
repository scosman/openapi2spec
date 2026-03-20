"""OpenAPI spec loader - fetches from URL or file."""

import json
from pathlib import Path

import httpx


def load_spec(source: str) -> dict:
    """Load OpenAPI spec from URL or file path.

    Args:
        source: URL (http:// or https://) or file path

    Returns:
        Parsed JSON dict

    Raises:
        ValueError: On fetch failure, parse failure, or validation failure
    """
    if source.startswith("http://") or source.startswith("https://"):
        raw = _fetch_url(source)
    else:
        raw = _read_file(source)

    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse OpenAPI spec: invalid JSON - {e}") from e

    if not isinstance(spec, dict):
        raise ValueError("Not a valid OpenAPI spec: expected a JSON object")
    if "openapi" not in spec:
        raise ValueError("Not a valid OpenAPI spec: missing 'openapi' key")
    if "paths" not in spec:
        raise ValueError("Not a valid OpenAPI spec: missing 'paths' key")

    return spec


def _fetch_url(url: str) -> str:
    """Fetch spec from URL."""
    try:
        response = httpx.get(url, timeout=10.0, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.HTTPStatusError as e:
        raise ValueError(
            f"Failed to fetch OpenAPI spec from {url}: HTTP {e.response.status_code}"
        ) from e
    except httpx.RequestError as e:
        raise ValueError(f"Failed to fetch OpenAPI spec from {url}: {e}") from e


def _read_file(path: str) -> str:
    """Read spec from file."""
    file_path = Path(path)
    if not file_path.exists():
        raise ValueError(f"File not found: {path}")
    return file_path.read_text()
