---
status: complete
---

# Architecture: API Skill Generator

## Overview

A straightforward pipeline: load spec → parse/resolve → generate files. No persistent state, no concurrency, no background processing. Each run is a pure function from inputs to output files.

This project is small enough for a single architecture doc.

## Dependencies

| Package | Purpose | Rationale |
|---------|---------|-----------|
| `httpx` | HTTP fetching | Modern, well-maintained. Used to fetch OpenAPI spec from URL. |
| `argparse` (stdlib) | CLI argument parsing | Simple enough interface; no need for click/typer. |
| `json` (stdlib) | JSON parsing | Standard. |
| `pathlib` (stdlib) | File path handling | Cleaner than os.path. |
| `pytest` | Testing | Standard Python test framework. |

No OpenAPI-specific libraries. The spec structure is well-defined JSON — we parse it directly. `$ref` resolution is implemented as a simple utility function (see below).

## Module Structure

```
openapi2skill/
  __main__.py          # CLI entry point (enables `uv run openapi2skill`)
  loader.py            # Fetch/read and validate the OpenAPI spec
  resolver.py          # $ref resolution
  parser.py            # Extract structured endpoint data from the spec
  generator.py         # Produce SKILL.md and reference markdown files
  writer.py            # Handle output directory, file naming, writing
```

## Data Flow

```
CLI args
  │
  ▼
loader.load_spec(spec_source: str) → dict
  │  Fetches URL or reads file, parses JSON, validates basic structure
  │
  ▼
resolver.resolve_refs(spec: dict) → dict
  │  Resolves all $ref pointers in-place, returns fully-inlined spec
  │
  ▼
parser.parse_endpoints(spec: dict) → list[Endpoint]
  │  Extracts structured endpoint data, groups by tag
  │
  ▼
generator.generate_skill_md(preamble: str, endpoints: list[Endpoint]) → str
generator.generate_reference_md(endpoint: Endpoint) → str
  │  Produces markdown strings (no I/O)
  │
  ▼
writer.write_output(output_dir: str, skill_md: str, references: dict[str, str])
  │  Creates timestamped subdirectory, writes files, handles naming collisions
  │
  ▼
Files on disk
```

## Data Model

### Endpoint (dataclass)

```python
@dataclass
class Endpoint:
    path: str               # e.g. "/api/users/{id}"
    method: str             # e.g. "POST" (uppercase)
    summary: str            # From operation summary, operationId, or method+path fallback
    description: str        # Full description or ""
    tag: str                # First tag, or "Other"
    parameters: list[Parameter]
    request_body: RequestBody | None
    responses: list[Response]

@dataclass
class Parameter:
    name: str
    location: str           # "path", "query", "header"
    type: str               # Rendered type string, e.g. "integer", "array of string"
    required: bool
    description: str
    default: str | None     # String representation of default value

@dataclass
class RequestBody:
    content_type: str       # e.g. "application/json"
    fields: list[Field]
    example: dict | None    # Raw example from spec, if present

@dataclass
class Field:
    name: str               # Dot notation for nested: "address.street"
    type: str               # Rendered type string
    required: bool
    description: str
    constraints: str        # Enum values, min/max, pattern, etc. or ""

@dataclass
class Response:
    status_code: str        # e.g. "200", "422"
    description: str
    fields: list[Field]
    example: dict | None
```

## Module Details

### loader.py

```python
def load_spec(source: str) -> dict:
    """Load OpenAPI spec from URL or file path. Returns parsed JSON dict."""
```

- If `source` starts with `http://` or `https://`: use `httpx.get()` with a reasonable timeout (10s)
- Otherwise: read from file using `pathlib.Path`
- Parse JSON; raise `ValueError` on parse failure
- Validate: check that `openapi` key exists and `paths` key exists
- Raise `ValueError` with descriptive message on validation failure

### resolver.py

```python
def resolve_refs(spec: dict) -> dict:
    """Resolve all $ref pointers in the spec, returning a fully-inlined copy."""
```

- Deep-copy the spec first (don't mutate the input)
- Walk the entire tree recursively
- When a dict has a `$ref` key with a value like `#/components/schemas/User`:
  - Split the path on `/`, skip the `#`
  - Navigate to that location in the **original** spec
  - Replace the `$ref` dict with the resolved content
- Handle circular references: if a `$ref` points to something already being resolved, stop recursion and leave a `{"type": "object", "description": "(circular reference)"}` placeholder
- This handles the common OpenAPI patterns. Edge cases like external file references (`file://...`) are out of scope.

### parser.py

```python
def parse_endpoints(spec: dict) -> list[Endpoint]:
    """Extract all endpoints from a resolved OpenAPI spec."""
```

- Iterate over `spec["paths"]`, then each method within each path
- For each operation, extract:
  - `summary`: prefer `summary`, fall back to `operationId`, then `"{METHOD} {path}"`
  - `description`: from operation `description` or `""`
  - `tag`: first item in `tags` list, or `"Other"`
  - Parameters from both path-level and operation-level `parameters` (operation overrides path)
  - Request body from `requestBody` → `content` → `application/json` → `schema`
  - Responses from `responses` dict
- Schema-to-fields conversion:
  - Object schemas: each property becomes a `Field`. Required determined by the schema's `required` array.
  - Nested objects: flatten with dot notation (e.g. `address.street`), depth limit of 3 levels
  - Arrays: type rendered as `"array of {itemType}"`
  - `allOf`: merge all sub-schemas into one
  - `oneOf`/`anyOf`: render as `"one of: TypeA, TypeB"`
  - Enums: include in constraints as `"One of: val1, val2, val3"`

```python
def group_by_tag(endpoints: list[Endpoint], spec: dict) -> list[tuple[str, list[Endpoint]]]:
    """Group endpoints by tag, ordered by the spec's top-level tags array."""
```

- Returns list of `(tag_name, endpoints)` tuples
- Ordering: tags listed in `spec.get("tags", [])` come first (in that order), then any remaining tags in order of first encounter
- "Other" group (untagged) comes last

### generator.py

Pure functions that produce markdown strings. No I/O, no side effects.

```python
def generate_skill_md(preamble: str, grouped_endpoints: list[tuple[str, list[Endpoint]]], filenames: dict[str, str]) -> str:
    """Generate the SKILL.md content."""
```

- Starts with `preamble` verbatim
- Adds `## API Reference` header
- For each tag group: `### {Tag Name}` header, then a markdown table
- Table escaping: pipe `|` replaced with `\|`, newlines replaced with spaces in Name and Description cells
- Description truncated to 100 chars with `...` if longer
- Details column links to the reference filename via `filenames` dict (keyed by `"{method}_{path}"`)

```python
def generate_reference_md(endpoint: Endpoint) -> str:
    """Generate a reference markdown file for one endpoint."""
```

- Generates the full reference file per the format in the functional spec
- Sections are conditionally included based on available data
- Examples rendered as fenced JSON code blocks

### writer.py

```python
def generate_filename(method: str, path: str) -> str:
    """Generate a reference filename from method and path."""

def write_output(base_output_dir: str, skill_md: str, references: list[tuple[str, str]]) -> str:
    """Write all output files. Returns the path of the created timestamped directory."""
```

- `generate_filename`: lowercase method + path segments joined with `_`, braces stripped. e.g. `POST /api/users/{id}/roles` → `post_api_users_id_roles.md`
- `write_output`:
  - Creates `{base_output_dir}/{timestamp}/` where timestamp is `YYYY-MM-DD_HHMMSS`
  - Creates `reference/` subdirectory
  - Detects filename collisions across all references; appends `_2`, `_3` etc. and prints warning to stderr
  - Writes `SKILL.md` and all reference files
  - Returns the created directory path (printed to stdout by CLI for scripting)

## CLI Entry Point (main.py)

```python
def main():
    args = parse_args()  # argparse with --spec (required), --preamble (optional), --output
    
    spec = load_spec(args.spec)
    spec = resolve_refs(spec)
    endpoints = parse_endpoints(spec)
    grouped = group_by_tag(endpoints, spec)
    filenames = assign_filenames(endpoints)  # writer.generate_filename + collision handling
    
    preamble = Path(args.preamble).read_text() if args.preamble else DEFAULT_PREAMBLE
    
    skill_md = generate_skill_md(preamble, grouped, filenames)
    references = [(filenames[ep_key], generate_reference_md(ep)) for ep_key, ep in ...]
    
    output_path = write_output(args.output, skill_md, references)
    print(f"Skill generated: {output_path}")
```

- All errors surface as exceptions caught at the top level
- Errors print to stderr and exit with code 1
- Success prints the output directory path to stdout

## Error Handling

- **Network errors** (fetching spec): caught by httpx, re-raised as a clear message ("Failed to fetch OpenAPI spec from {url}: {reason}")
- **JSON parse errors**: "Failed to parse OpenAPI spec: invalid JSON"
- **Validation errors**: "Not a valid OpenAPI spec: missing 'paths' key"
- **File not found** (preamble or spec file): "File not found: {path}"
- **Write errors**: "Failed to write output: {reason}"

All errors are fatal (exit 1). No partial output is written — the timestamped directory is only created once we're ready to write.

## Testing Strategy

**Framework:** pytest

**Test categories:**

1. **Unit tests for each module:**
   - `test_loader.py`: test URL vs file detection, JSON validation, error messages
   - `test_resolver.py`: test $ref resolution including nested refs, circular refs
   - `test_parser.py`: test endpoint extraction, schema flattening, tag grouping, edge cases (missing fields, allOf/oneOf)
   - `test_generator.py`: test markdown output, table escaping, section inclusion/exclusion, description truncation
   - `test_writer.py`: test filename generation, collision detection, directory creation

2. **Integration test:**
   - Feed a real-ish OpenAPI spec (included as a test fixture) through the full pipeline
   - Verify the output files exist and contain expected content
   - Use assertion-based checks: verify files exist, contain expected headers/sections, correct endpoint count, etc.

**Test fixtures:**
- A small but representative OpenAPI spec JSON covering: multiple tags, path/query params, request bodies, multiple response codes, `$ref` usage, nested objects, arrays, enums, examples
- A sample preamble file

**No mocking of the file system** — tests write to a tmp directory (pytest `tmp_path` fixture). HTTP fetching tests mock `httpx` responses.
