---
status: complete
---

# Phase 2: Parser - Endpoint Extraction and Schema-to-Fields Conversion

## Overview

Implement `parser.py` to transform a resolved OpenAPI spec dict into a list of structured `Endpoint` objects. This is the core parsing logic that bridges spec loading (phase 1) and markdown generation (phase 3).

## Steps

### 1. Create `openapi2skill/parser.py` with core functions

Create the parser module with the following functions:

```python
def parse_endpoints(spec: dict) -> list[Endpoint]:
    """Extract all endpoints from a resolved OpenAPI spec."""

def group_by_tag(endpoints: list[Endpoint], spec: dict) -> list[tuple[str, list[Endpoint]]]:
    """Group endpoints by tag, ordered by the spec's top-level tags array."""
```

### 2. Implement endpoint extraction in `parse_endpoints`

- Iterate over `spec["paths"]`, then each HTTP method within each path
- For each operation, extract:
  - `path`: the URL path string
  - `method`: uppercase HTTP method (GET, POST, PUT, DELETE, PATCH)
  - `summary`: prefer `summary`, fall back to `operationId`, then `"{METHOD} {path}"`
  - `description`: from operation `description` or empty string
  - `tag`: first item in `tags` list, or `"Other"`
  - `parameters`: merge path-level and operation-level params (operation overrides path)
  - `request_body`: extract from `requestBody.content.application/json.schema`
  - `responses`: extract from `responses` dict

### 3. Implement parameter extraction helper

```python
def _extract_parameters(path_item: dict, operation: dict) -> list[Parameter]:
    """Extract and merge path-level and operation-level parameters."""
```

- Merge parameters from path-level and operation-level
- Operation parameters override path-level ones with same name+location
- Extract: name, location (in), type, required, description, default

### 4. Implement schema-to-fields conversion

```python
def _schema_to_fields(schema: dict, prefix: str = "", depth: int = 0) -> list[Field]:
    """Convert an OpenAPI schema to a list of Field objects."""
```

- Object schemas: each property becomes a Field
- Required determined by the schema's `required` array
- Nested objects: flatten with dot notation (e.g. `address.street`), depth limit of 3
- Arrays: type rendered as `"array of {itemType}"`
- `allOf`: merge all sub-schemas into one
- `oneOf`/`anyOf`: render type as `"one of: TypeA, TypeB"`
- Enums: include in constraints as `"One of: val1, val2, val3"`

### 5. Implement type rendering helper

```python
def _render_type(schema: dict) -> str:
    """Render a schema's type as a human-readable string."""
```

- Simple types: `"string"`, `"integer"`, `"number"`, `"boolean"`, `"object"`
- Arrays: `"array of {itemType}"`
- `$ref`: should already be resolved, but handle gracefully
- `oneOf`/`anyOf`: `"one of: TypeA, TypeB"`

### 6. Implement request body extraction

```python
def _extract_request_body(request_body: dict) -> RequestBody | None:
    """Extract RequestBody from OpenAPI requestBody spec."""
```

- Get content type (prefer `application/json`)
- Convert schema to fields
- Extract example if present

### 7. Implement response extraction

```python
def _extract_responses(responses: dict) -> list[Response]:
    """Extract Response objects from OpenAPI responses spec."""
```

- For each status code, extract description, fields, and example
- Only include content if `application/json` schema exists

### 8. Implement tag grouping in `group_by_tag`

- Tags listed in `spec.get("tags", [])` come first (in that order)
- Remaining tags appear in order of first encounter
- "Other" group (untagged endpoints) comes last

### 9. Create `tests/test_parser.py` with comprehensive tests

Test cases:
- Basic endpoint extraction with all fields
- Missing summary/description/operationId fallbacks
- Tag grouping with spec-defined tags and ad-hoc tags
- Path parameters extraction
- Query parameters with defaults
- Request body with nested objects
- Request body with enum fields
- Array types in responses
- `allOf` schema merging
- `oneOf`/`anyOf` schema handling
- Empty paths (returns empty list)
- Endpoint with no tags (goes to "Other")
- Nested object flattening with depth limit
- Circular reference placeholder handling

## Tests

Located in `tests/test_parser.py`:

```python
# Core parsing tests
def test_parse_endpoints_basic() -> None
def test_parse_endpoints_empty_paths() -> None
def test_parse_endpoints_missing_summary() -> None
def test_parse_endpoints_missing_summary_and_operation_id() -> None
def test_parse_endpoints_no_tags() -> None
def test_parse_endpoints_multiple_tags() -> None

# Parameter extraction tests
def test_extract_parameters_path_params() -> None
def test_extract_parameters_query_params_with_default() -> None
def test_extract_parameters_merge_path_and_operation() -> None
def test_extract_parameters_operation_overrides_path() -> None

# Request body tests
def test_extract_request_body_simple() -> None
def test_extract_request_body_nested_object() -> None
def test_extract_request_body_with_enum() -> None
def test_extract_request_body_with_example() -> None

# Response tests
def test_extract_responses_simple() -> None
def test_extract_responses_array_type() -> None
def test_extract_responses_multiple_status_codes() -> None

# Schema conversion tests
def test_schema_to_fields_simple_object() -> None
def test_schema_to_fields_nested_flattening() -> None
def test_schema_to_fields_depth_limit() -> None
def test_schema_to_fields_array_type() -> None
def test_schema_to_fields_allOf() -> None
def test_schema_to_fields_oneOf() -> None
def test_schema_to_fields_enum() -> None

# Tag grouping tests
def test_group_by_tag_basic() -> None
def test_group_by_tag_spec_tag_order() -> None
def test_group_by_tag_other_last() -> None
def test_group_by_tag_adhoc_tags_after_spec_tags() -> None

# Integration with sample spec
def test_parse_sample_spec() -> None
```

## Dependencies

- Uses `models.py` dataclasses from phase 1
- Input is a resolved spec (all `$ref`s already inlined via `resolver.py`)

## Edge Cases to Handle

1. **Empty spec (no paths)**: Return empty list
2. **Missing summary/operationId**: Use `"{METHOD} {path}"` as fallback
3. **Missing description**: Use empty string
4. **No tags on endpoint**: Use `"Other"`
5. **Nested objects**: Flatten with dot notation, limit to 3 levels deep
6. **Circular references**: Already replaced with placeholder by resolver
7. **allOf merging**: Merge properties from all sub-schemas
8. **oneOf/anyOf**: Render as union type string
9. **Array items**: Resolve item type for proper display
10. **No request body**: Return `None`
11. **Multiple content types**: Prefer `application/json`, skip others

## Verification

- Run `uv run pytest tests/test_parser.py -v` - all tests pass
- Run `uv run ruff check openapi2skill/parser.py` - no lint errors
- Run `uv run ruff format openapi2skill/parser.py` - formatted correctly
