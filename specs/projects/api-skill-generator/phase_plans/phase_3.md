---
status: complete
---

# Phase 3: Generators, Writer, and CLI

## Overview

Implement the final pieces of the pipeline: `generator.py` (produces SKILL.md and reference markdown), `writer.py` (file naming, timestamped output, collision detection), and `__main__.py` (CLI entry point). This completes the tool so users can run `uv run openapi2skill --spec <path>` to generate agent skills.

## Steps

### 1. Create `openapi2skill/generator.py`

Pure functions that produce markdown strings. No I/O, no side effects.

**Functions to implement:**

```python
DEFAULT_PREAMBLE = """This skill describes the endpoints and functionality of an API. Use the summary table below to find relevant endpoints, then read the linked reference files for full request/response details. You can call these APIs using curl or any HTTP client."""

def escape_table_cell(text: str) -> str:
    """Escape text for safe inclusion in a markdown table cell.
    - Replace | with \|
    - Replace newlines with space
    """

def truncate_description(text: str, max_length: int = 100) -> str:
    """Truncate text to max_length, adding '...' if truncated."""

def generate_skill_md(
    preamble: str,
    grouped_endpoints: list[tuple[str, list[Endpoint]]],
    filenames: dict[str, str],
) -> str:
    """Generate the SKILL.md content.

    Args:
        preamble: Markdown to include verbatim at the top
        grouped_endpoints: List of (tag_name, endpoints) tuples
        filenames: Dict mapping "{method}_{path}" to reference filenames

    Returns:
        Complete SKILL.md content
    """

def generate_reference_md(endpoint: Endpoint) -> str:
    """Generate a reference markdown file for one endpoint.

    Returns:
        Complete reference file content
    """
```

**Implementation details:**

- `generate_skill_md`:
  - Start with preamble verbatim
  - Add `## API Reference` header
  - For each tag group: `### {Tag Name}` header, then markdown table
  - Table columns: Endpoint, Method, Name, Description, Details
  - Details column links to reference file: `[Details](reference/{filename})`
  - Escape Name and Description cells for table safety
  - Truncate description to 100 chars

- `generate_reference_md`:
  - Title: `# {summary}`
  - Method/Path: `**{METHOD} {path}**`
  - Full description (not truncated)
  - Request section with Path Parameters, Query Parameters, Request Body subsections
  - Responses section with status codes
  - Examples as fenced JSON code blocks
  - Only include sections that have content

### 2. Create `openapi2skill/writer.py`

Handle file naming, timestamped output directories, and collision detection.

**Functions to implement:**

```python
def generate_filename(method: str, path: str) -> str:
    """Generate a reference filename from method and path.

    Examples:
        GET /users -> get_users.md
        POST /api/users/{id}/roles -> post_api_users_id_roles.md
    """

def assign_filenames(endpoints: list[Endpoint]) -> dict[str, str]:
    """Assign unique filenames to endpoints.

    Returns:
        Dict mapping "{method}_{path}" to filename
    """

def write_output(
    base_output_dir: str,
    skill_md: str,
    references: list[tuple[str, str]],
) -> str:
    """Write all output files.

    Args:
        base_output_dir: Base output directory (e.g., "./output")
        skill_md: SKILL.md content
        references: List of (filename, content) tuples

    Returns:
        Path to the created timestamped directory

    Raises:
        OSError: On write failure
    """
```

**Implementation details:**

- `generate_filename`:
  - Lowercase method prefix
  - Path segments joined with `_`, stripping leading slash
  - Strip braces from path params: `{id}` -> `id`
  - Add `.md` suffix

- `assign_filenames`:
  - Track used filenames
  - If collision, append `_2`, `_3`, etc.
  - Log warning to stderr on collision

- `write_output`:
  - Create timestamped subdirectory: `YYYY-MM-DD_HHMMSS`
  - Create `reference/` subdirectory
  - Write `SKILL.md` and all reference files
  - Return the created directory path

### 3. Create `openapi2skill/__main__.py`

CLI entry point that wires everything together.

```python
import argparse
import sys
from pathlib import Path

from openapi2skill.loader import load_spec
from openapi2skill.resolver import resolve_refs
from openapi2skill.parser import parse_endpoints, group_by_tag
from openapi2skill.generator import (
    DEFAULT_PREAMBLE,
    generate_skill_md,
    generate_reference_md,
)
from openapi2skill.writer import assign_filenames, write_output


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

def main() -> None:
    """Main entry point."""

if __name__ == "__main__":
    main()
```

**CLI behavior:**

- `--spec` (required): URL or file path to OpenAPI JSON spec
- `--preamble` (optional): Path to preamble markdown file
- `--output` (optional, default `./output`): Output directory

- Success: print output directory path to stdout, exit 0
- Failure: print error to stderr, exit 1
- Empty spec (no paths): warning to stderr, still generate with empty API Reference

### 4. Create tests for `generator.py`

Test file: `tests/test_generator.py`

**Test cases:**
- `test_escape_table_cell_pipe`: Pipe characters are escaped
- `test_escape_table_cell_newlines`: Newlines replaced with space
- `test_truncate_description_no_change`: Short text unchanged
- `test_truncate_description_with_ellipsis`: Long text truncated with "..."
- `test_generate_skill_md_basic`: Basic SKILL.md generation
- `test_generate_skill_md_with_preamble`: Preamble included verbatim
- `test_generate_skill_md_empty_endpoints`: Empty spec produces empty API Reference
- `test_generate_skill_md_multiple_tags`: Multiple tag groups
- `test_generate_reference_md_basic`: Basic reference file generation
- `test_generate_reference_md_with_path_params`: Path parameters section
- `test_generate_reference_md_with_query_params`: Query parameters with defaults
- `test_generate_reference_md_with_request_body`: Request body section
- `test_generate_reference_md_with_example`: Example code block included
- `test_generate_reference_md_without_example`: No example section when missing
- `test_generate_reference_md_multiple_responses`: Multiple response codes

### 5. Create tests for `writer.py`

Test file: `tests/test_writer.py`

**Test cases:**
- `test_generate_filename_simple`: `GET /users` -> `get_users.md`
- `test_generate_filename_with_path_param`: `POST /users/{id}` -> `post_users_id.md`
- `test_generate_filename_nested_path`: Complex path handling
- `test_assign_filenames_no_collision`: Unique filenames assigned
- `test_assign_filenames_collision`: Collisions resolved with `_2`, `_3`
- `test_write_output_creates_directory`: Timestamped directory created
- `test_write_output_creates_reference_subdir`: reference/ subdirectory created
- `test_write_output_writes_skill_md`: SKILL.md written correctly
- `test_write_output_writes_references`: Reference files written correctly
- `test_write_output_returns_path`: Returns the created directory path

### 6. Create tests for CLI (`__main__.py`)

Test file: `tests/test_main.py`

**Test cases:**
- `test_main_success`: Full pipeline runs successfully
- `test_main_with_preamble_file`: Custom preamble loaded
- `test_main_missing_spec_file`: Error on missing spec file
- `test_main_invalid_spec`: Error on invalid spec
- `test_main_output_printed`: Output path printed to stdout
- `test_main_empty_spec_warning`: Warning printed for empty spec

### 7. Create integration test

Test file: `tests/test_integration.py`

**Test cases:**
- `test_full_pipeline_with_sample_spec`:
  - Load sample_spec.json
  - Run full pipeline
  - Verify SKILL.md exists and contains expected content
  - Verify reference files exist
  - Verify file count matches endpoint count

### 8. Run tests and fix issues

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format .
```

Iterate until all tests pass and linting is clean.

### 9. Code review via sub-agent

Spawn a CR sub-agent with:
> A coding agent just implemented phase 3 of api-skill-generator. Review using `git diff`. The spec is at specs/projects/api-skill-generator/

Iterate on feedback until clean.

## Dependencies

- No new dependencies (uses stdlib for argparse, pathlib, datetime, sys)
- Reuses models from `models.py`
- Uses loader, resolver, parser from phases 1 and 2

## Testing Strategy

- Unit tests for each module with >95% coverage
- Integration test using sample_spec.json fixture
- Tests write to pytest `tmp_path` fixture (no mocking of file system)
- CLI tests capture stdout/stderr for verification
