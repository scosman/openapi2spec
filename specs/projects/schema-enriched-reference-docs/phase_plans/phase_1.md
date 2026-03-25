---
status: complete
---

# Phase 1: Resolver + Models + SchemaCollector

## Overview

Implement the foundation for schema collection: annotate `$ref` resolutions with `x-schema-name`, add the `Schema` dataclass and `schemas` field to `Endpoint`, and implement the `SchemaCollector` class with name-derivation helpers.

## Steps

### 1. resolver.py — Annotate `$ref` resolutions with `x-schema-name`

**File:** `openapi2skill/resolver.py`

**Change:** In `resolve_in_place`, after resolving a `$ref` that points to `#/components/schemas/...`, add `x-schema-name` to the resolved object.

**Location:** After line 42 (`obj.update(ref_copy)`)

```python
if ref_path.startswith("#/components/schemas/"):
    schema_name = ref_path.split("/")[-1]
    obj["x-schema-name"] = schema_name
```

Also handle circular references: when creating the circular placeholder, add `x-schema-name` if the ref path is a schema reference.

### 2. models.py — Add `Schema` dataclass and `schemas` field on `Endpoint`

**File:** `openapi2skill/models.py`

**Add `Schema` dataclass:**

```python
@dataclass
class Schema:
    """Represents a named object schema for the Schemas section."""

    name: str
    description: str
    fields: list["Field"]
```

**Modify `Endpoint` dataclass:** Add `schemas: list[Schema]` field after `responses`.

### 3. parser.py — Implement `SchemaCollector` class

**File:** `openapi2skill/parser.py`

**Add imports:** Import `Schema` from models.

**Add `SchemaCollector` class:**

```python
class SchemaCollector:
    def __init__(self):
        self._schemas: dict[str, Schema] = {}
        self._fingerprints: dict[str, str] = {}

    def register(self, name: str, description: str, fields: list[Field]) -> str:
        fingerprint = self._make_fingerprint(fields)
        if fingerprint in self._fingerprints:
            return self._fingerprints[fingerprint]
        final_name = name
        if name in self._schemas:
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
        return list(self._schemas.values())

    @staticmethod
    def _make_fingerprint(fields: list[Field]) -> str:
        parts = []
        for f in sorted(fields, key=lambda x: x.name):
            parts.append(f"{f.name}:{f.type}:{f.required}")
        return "|".join(parts)
```

**Add helper functions:**

```python
def _derive_schema_name(schema: dict, field_name: str) -> str:
    if "x-schema-name" in schema:
        return schema["x-schema-name"]
    return "".join(segment.capitalize() for segment in field_name.split("_"))
```

### 4. Update `_extract_endpoint` to create collector and pass schemas

**File:** `openapi2skill/parser.py`

Modify `_extract_endpoint` to:
1. Create a `SchemaCollector` instance
2. Pass it to `_extract_request_body` and `_extract_responses` (Phase 2)
3. Attach `collector.schemas` to the `Endpoint`

For Phase 1, just create the collector and attach empty schemas list.

## Tests

### test_resolver.py — New tests

1. `test_resolve_ref_preserves_schema_name`: Verify `x-schema-name` is added for `#/components/schemas/X`
2. `test_resolve_ref_no_schema_name_for_non_schema_ref`: Verify NOT added for non-schema refs
3. `test_resolve_circular_ref_preserves_schema_name`: Verify circular ref gets `x-schema-name`

### test_parser.py — New tests

1. `test_schema_collector_basic`: Register a schema, verify retrieval
2. `test_schema_collector_dedup_identical`: Two identical schemas → same name
3. `test_schema_collector_conflict_different`: Different schemas with same name → V2 suffix
4. `test_schema_collector_fingerprint_order_independent`: Same fields in different order → same fingerprint
5. `test_derive_schema_name_from_ref`: Prefer `x-schema-name`
6. `test_derive_schema_name_from_field`: snake_case → PascalCase

## Verification

- Run `uv run ruff check .` — lint clean
- Run `uv run ruff format .` — format clean
- Run `uv run pytest` — all tests pass
