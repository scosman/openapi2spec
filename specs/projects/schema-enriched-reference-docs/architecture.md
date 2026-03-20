---
status: complete
---

# Architecture: Schema-Enriched Reference Docs

## Overview

This is a set of targeted changes to four existing modules (`resolver.py`, `models.py`, `parser.py`, `generator.py`) plus their tests. No new modules or files are needed.

## Data Model Changes

### New: `Schema` dataclass (in `models.py`)

```python
@dataclass
class Schema:
    name: str
    description: str
    fields: list[Field]
```

Represents a named object schema to be rendered in the Schemas section of a reference file.

### Modified: `Endpoint` dataclass

Add a `schemas` field:

```python
@dataclass
class Endpoint:
    path: str
    method: str
    summary: str
    description: str
    tag: str
    parameters: list[Parameter]
    request_body: RequestBody | None
    responses: list[Response]
    schemas: list[Schema]  # NEW — collected during parsing
```

`schemas` is an ordered list (insertion order = order of first reference while walking request body then responses top-down). This ordering determines the display order in the Schemas section.

## Module Changes

### 1. `resolver.py` — Preserve Schema Names

**Change**: When resolving a `$ref` that points into `#/components/schemas/...`, add an `x-schema-name` key to the inlined dict.

In `resolve_in_place`, after `obj.update(ref_copy)` on line 42:

```python
# Extract schema name from $ref path if it's a component schema
if ref_path.startswith("#/components/schemas/"):
    schema_name = ref_path.split("/")[-1]
    obj["x-schema-name"] = schema_name
```

This is safe because `x-` prefixed keys are extension fields in OpenAPI and won't collide with real schema properties. Only schema refs get annotated — parameter refs, response refs, etc. don't match the prefix.

Circular references already produce a placeholder `{"type": "object", "description": "(circular reference)"}`. With this change, also add `x-schema-name` so the parser can reference the schema by name even for circular refs.

### 2. `parser.py` — Schema Collection During Parsing

#### New: `SchemaCollector` class

A mutable collector threaded through the parsing functions for a single endpoint:

```python
class SchemaCollector:
    def __init__(self):
        self._schemas: dict[str, Schema] = {}       # name -> Schema (insertion-ordered)
        self._fingerprints: dict[str, str] = {}      # fingerprint -> name (for dedup)

    def register(self, name: str, description: str, fields: list[Field]) -> str:
        """Register a schema. Returns the final name (may differ if conflict resolved).

        - If a schema with this name exists and is structurally identical, return existing name.
        - If a schema with this name exists but differs, append V2/V3/... and register under new name.
        - Otherwise, register under the given name.
        """
        fingerprint = self._make_fingerprint(fields)

        # Check if an identical schema already exists (under any name)
        if fingerprint in self._fingerprints:
            return self._fingerprints[fingerprint]

        # Check for name conflict
        final_name = name
        if name in self._schemas:
            # Different schema, same name — find next available suffix
            suffix = 2
            while f"{name}V{suffix}" in self._schemas:
                suffix += 1
            final_name = f"{name}V{suffix}"

        schema = Schema(name=final_name, description=description, fields=fields)
        self._schemas[final_name] = schema
        self._fingerprints[fingerprint] = final_name
        return final_name

    @property
    def schemas(self) -> list[Schema]:
        """Return schemas in insertion order."""
        return list(self._schemas.values())

    @staticmethod
    def _make_fingerprint(fields: list[Field]) -> str:
        """Create a structural fingerprint for dedup comparison."""
        parts = []
        for f in sorted(fields, key=lambda x: x.name):
            parts.append(f"{f.name}:{f.type}:{f.required}")
        return "|".join(parts)
```

#### Modified: `_schema_to_fields()`

Add a `collector: SchemaCollector | None` parameter. When `collector` is `None`, behavior is unchanged (backward-compatible for any callers that don't need schemas).

The key logic change is at the two points where the current code produces an opaque "object" or "array of object":

**Point 1 — Object at depth limit or without properties (line ~322-334):**

Currently: returns a `Field` with `type=_render_type(prop_schema)` which yields "object" or "array of object".

New behavior: if the schema has properties (resolvable into fields), create a Schema via the collector:

```python
if prop_type == "object" and "properties" in prop_schema and depth < 2:
    # Existing: flatten with dot notation
    nested_fields = _schema_to_fields(prop_schema, f"{field_name}.", depth + 1, collector)
    fields.extend(nested_fields)
elif collector is not None and _should_create_schema(prop_schema):
    # NEW: register as named schema instead of opaque "object"
    schema_name = _derive_schema_name(prop_schema, prop_name)
    schema_fields = _schema_to_fields(prop_schema, "", 0, collector)
    final_name = collector.register(schema_name, prop_schema.get("description", ""), schema_fields)
    rendered_type = _render_type_with_schema(prop_schema, final_name)
    fields.append(Field(name=field_name, type=rendered_type, required=is_required,
                        description=description, constraints=constraints))
else:
    # Fallback: existing behavior
    fields.append(Field(name=field_name, type=_render_type(prop_schema), ...))
```

**Point 2 — Array items that are objects:**

When `_render_type` would produce "array of object", instead produce "array of SchemaName" and register the items schema.

#### New helper: `_should_create_schema(schema: dict) -> bool`

Returns `True` if the schema has enough structure to warrant a schema definition:
- Has `properties` with at least one property, OR
- Has `x-schema-name` (it was a named component in the spec), OR
- Is an array whose `items` has properties or `x-schema-name`

Returns `False` for bare `{"type": "object"}` with no properties and no name — these stay as "object".

#### New helper: `_derive_schema_name(schema: dict, field_name: str) -> str`

```python
def _derive_schema_name(schema: dict, field_name: str) -> str:
    # Prefer the original $ref name if preserved
    if "x-schema-name" in schema:
        return schema["x-schema-name"]
    # Derive from field name: snake_case -> PascalCase
    return "".join(segment.capitalize() for segment in field_name.split("_"))
```

#### New helper: `_render_type_with_schema(schema: dict, schema_name: str) -> str`

Produces the type string using the schema name:
- Object → `schema_name` (e.g., `TaskMetadata`)
- Array of objects → `array of {schema_name}` (e.g., `array of QuestionAndAnswer`)

#### Modified: `_extract_endpoint()`

Create a `SchemaCollector` per endpoint, pass it through to `_extract_request_body()` and `_extract_responses()`, then attach `collector.schemas` to the `Endpoint`.

#### Modified: `_extract_request_body()` and `_extract_responses()`

Accept a `collector` parameter and pass it to `_schema_to_fields()`.

#### Modified: `_render_type()`

No changes needed — this function is still used for primitive types and as a fallback. The new schema-aware path goes through `_render_type_with_schema()`.

### 3. `generator.py` — Render Schemas Section

#### Modified: `generate_reference_md()`

After the Responses section, if `endpoint.schemas` is non-empty, append:

```markdown
## Schemas

### SchemaName

Description text (if available).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| field_a | string | Yes | ... |
| nested | OtherSchema | No | ... |
```

Implementation: new function `_generate_schemas_section(schemas: list[Schema]) -> list[str]` that iterates over schemas and builds the markdown lines. Uses the same field-table formatting as request body fields (including constraints in description).

## Data Flow

```
OpenAPI JSON
    │
    ▼
resolver.resolve_refs()     ← adds x-schema-name to $ref resolutions
    │
    ▼
parser.parse_endpoints()    ← creates SchemaCollector per endpoint
    │                         threads it through _extract_request_body,
    │                         _extract_responses, _schema_to_fields
    │                         attaches collector.schemas to Endpoint
    ▼
generator.generate_reference_md()  ← renders Schemas section from endpoint.schemas
    │
    ▼
Reference markdown file
```

## Testing Strategy

All existing tests must continue to pass. Tests use `pytest`, run with `uv run pytest`.

### `test_resolver.py` — New tests

- `test_resolve_ref_preserves_schema_name`: Verify `x-schema-name` is added when resolving a `#/components/schemas/X` ref.
- `test_resolve_ref_no_schema_name_for_non_schema_ref`: Verify `x-schema-name` is NOT added for non-schema refs (e.g., `#/components/parameters/X`).
- `test_resolve_circular_ref_preserves_schema_name`: Verify circular ref placeholder gets `x-schema-name`.

### `test_parser.py` — New tests

- `test_schema_collector_basic`: Register a schema, verify retrieval.
- `test_schema_collector_dedup_identical`: Two identical schemas → same name returned.
- `test_schema_collector_conflict_different`: Two different schemas with same derived name → `V2` suffix.
- `test_schema_to_fields_with_collector_named_ref`: Schema with `x-schema-name` → schema registered, field type uses name.
- `test_schema_to_fields_with_collector_inline`: Inline object → PascalCase name derived from field name.
- `test_schema_to_fields_array_of_objects`: Array of objects → `array of SchemaName` type.
- `test_schema_to_fields_transitive`: Schema A references Schema B → both in collector.
- `test_schema_to_fields_no_properties_object`: Bare object without properties → stays "object", no schema created.
- `test_schema_to_fields_oneof_with_object_variants`: `oneOf` containing objects → variant schemas registered.
- `test_schema_to_fields_without_collector`: Passing `collector=None` → existing behavior unchanged.
- `test_derive_schema_name_from_ref`: `x-schema-name` is preferred.
- `test_derive_schema_name_from_field`: Snake_case → PascalCase.

### `test_generator.py` — New tests

- `test_reference_md_with_schemas`: Endpoint with schemas → Schemas section rendered at end.
- `test_reference_md_no_schemas`: Endpoint without schemas → no Schemas section.
- `test_schemas_section_field_table_format`: Verify table headers, constraints in descriptions.

### `test_integration.py` — New/updated tests

- Update the existing integration test to verify the generated reference files include Schemas sections where expected.

## No New Dependencies

All changes use the Python standard library. No new packages needed.
