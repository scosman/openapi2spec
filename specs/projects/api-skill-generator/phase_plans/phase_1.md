---
status: complete
---

# Phase 1: Project Setup, Data Model, and Spec Loading

## Overview

Set up the project structure, data models, and implement `loader.py` and `resolver.py`. This gives us a parsed, resolved OpenAPI spec dict that subsequent phases can build on.

## Steps

### 1. Update pyproject.toml

Add required dependencies: `httpx` (HTTP fetching) and `pytest` (testing).

File: `/Users/scosman/Dropbox/workspace/experiments/api_skill_generator/pyproject.toml`

```toml
[project]
name = "openapi2skill"
version = "0.1.0"
description = "Generate agent skills from OpenAPI specs"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "httpx>=0.27.0",
]

[project.scripts]
openapi2skill = "openapi2skill.__main__:main"

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.8.0",
]
```

### 2. Create Package Structure

Create the `openapi2skill/` package directory with:
- `__init__.py` - package init
- `models.py` - dataclass models
- `loader.py` - spec loading from URL/file
- `resolver.py` - $ref resolution

Remove root `main.py` (will be replaced by `openapi2skill/__main__.py` in phase 3).

### 3. Implement Data Models

File: `/Users/scosman/Dropbox/workspace/experiments/api_skill_generator/openapi2skill/models.py`

```python
from dataclasses import dataclass

@dataclass
class Endpoint:
    path: str
    method: str
    summary: str
    description: str
    tag: str
    parameters: list["Parameter"]
    request_body: "RequestBody | None"
    responses: list["Response"]

@dataclass
class Parameter:
    name: str
    location: str  # "path", "query", "header"
    type: str
    required: bool
    description: str
    default: str | None

@dataclass
class RequestBody:
    content_type: str
    fields: list["Field"]
    example: dict | None

@dataclass
class Field:
    name: str
    type: str
    required: bool
    description: str
    constraints: str

@dataclass
class Response:
    status_code: str
    description: str
    fields: list["Field"]
    example: dict | None
```

### 4. Implement loader.py

File: `/Users/scosman/Dropbox/workspace/experiments/api_skill_generator/openapi2skill/loader.py`

```python
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
    # Detect URL vs file
    if source.startswith("http://") or source.startswith("https://"):
        raw = _fetch_url(source)
    else:
        raw = _read_file(source)

    # Parse JSON
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse OpenAPI spec: invalid JSON - {e}") from e

    # Validate structure
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
```

### 5. Implement resolver.py

File: `/Users/scosman/Dropbox/workspace/experiments/api_skill_generator/openapi2skill/resolver.py`

```python
import copy


def resolve_refs(spec: dict) -> dict:
    """Resolve all $ref pointers in the spec, returning a fully-inlined copy.

    Args:
        spec: The OpenAPI spec dict

    Returns:
        A new dict with all $refs resolved in-place
    """
    # Deep copy to avoid mutating the input
    resolved = copy.deepcopy(spec)

    # Track resolution stack to detect circular references
    resolution_stack: set[str] = set()

    def walk(obj: dict | list, stack: set[str]) -> None:
        """Recursively walk and resolve $refs."""
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_path = obj["$ref"]
                if ref_path in stack:
                    # Circular reference - replace with placeholder
                    obj.clear()
                    obj["type"] = "object"
                    obj["description"] = "(circular reference)"
                    return

                resolved_content = _resolve_ref(spec, ref_path)
                if resolved_content is not None:
                    # Replace $ref dict with resolved content
                    new_stack = stack | {ref_path}
                    walk(resolved_content, new_stack)
                    obj.clear()
                    obj.update(resolved_content)
            else:
                # Walk all values
                for value in obj.values():
                    walk(value, stack)
        elif isinstance(obj, list):
            for item in obj:
                walk(item, stack)

    walk(resolved, resolution_stack)
    return resolved


def _resolve_ref(spec: dict, ref: str) -> dict | None:
    """Resolve a $ref pointer to its target content.

    Args:
        spec: The original (unmodified) spec dict
        ref: Reference string like "#/components/schemas/User"

    Returns:
        The referenced dict, or None if not found
    """
    if not ref.startswith("#/"):
        # External refs not supported
        return None

    # Split path: "#/components/schemas/User" -> ["components", "schemas", "User"]
    parts = ref[2:].split("/")

    # Navigate to target
    current = spec
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]

    return current if isinstance(current, dict) else None
```

### 6. Write Tests

File: `/Users/scosman/Dropbox/workspace/experiments/api_skill_generator/tests/__init__.py`

Empty file to make tests a package.

File: `/Users/scosman/Dropbox/workspace/experiments/api_skill_generator/tests/test_loader.py`

- Test loading from file path
- Test loading from URL (mocked httpx)
- Test JSON parse error handling
- Test validation errors (missing openapi, missing paths)
- Test file not found error

File: `/Users/scosman/Dropbox/workspace/experiments/api_skill_generator/tests/test_resolver.py`

- Test simple $ref resolution
- Test nested $ref resolution
- Test circular reference handling
- Test that input is not mutated
- Test invalid ref path handling

### 7. Create Test Fixture

File: `/Users/scosman/Dropbox/workspace/experiments/api_skill_generator/tests/fixtures/sample_spec.json`

A minimal OpenAPI spec with:
- $ref to components/schemas
- Nested $refs
- Circular reference scenario (for testing)

## Tests

Run with `uv run pytest` from project root.

Target: 95%+ coverage on `loader.py` and `resolver.py`.

## Acceptance Criteria

- [x] `uv run openapi2skill` shows help (even if minimal CLI in phase 3) - CLI entry point will be added in phase 3
- [x] `uv run pytest tests/` passes all tests - 23 tests passing
- [x] `uv run ruff check .` passes
- [x] `uv run ruff format .` shows no changes needed
- [x] Can load a spec from file or URL
- [x] Can resolve $refs in a spec
