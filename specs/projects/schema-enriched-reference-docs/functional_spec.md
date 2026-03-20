---
status: complete
---

# Functional Spec: Schema-Enriched Reference Docs

## Overview

Enhance the `openapi2skill` reference file generator so that every complex object type ("object", "array of object") is replaced with a named schema reference, and a **Schemas** section at the bottom of each reference file defines those schemas. A single reference file should contain everything needed to construct a valid request and understand the response.

## Behavior Changes

### 1. Named Schema References in Field Tables

Anywhere the current output renders a field type as `object` or `array of object`, the new output uses a named schema reference instead.

**Before:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| questions_and_answers | array of object | Yes | Questions with answers |
| task_metadata | object | Yes | Metadata about the model |

**After:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| questions_and_answers | array of QuestionAndAnswer | Yes | Questions with answers |
| task_metadata | TaskMetadata | Yes | Metadata about the model |

This applies to both request body field tables and response field tables.

### 2. Schemas Section

A new `## Schemas` section is appended to the end of each reference file (after Responses). It contains one subsection per schema used anywhere in the file.

Format:

```
## Schemas

### SchemaName

Description of the schema (from OpenAPI description field, if available).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| field_name | string | Yes | Field description |
| nested_field | OtherSchema | No | References another schema |
```

- Each schema lists its direct properties in a field table.
- If a schema's field is itself a complex object, it references another schema by name — and that schema is also included in the Schemas section (transitive inclusion).
- The Schemas section only appears if the endpoint has at least one schema to define.
- Schemas are listed in order of first reference (top-down through the file: request body fields first, then response fields).

### 3. Dot-Notation Flattening (Preserved)

The existing dot-notation flattening for simple nested objects is preserved. When a parent object has properties that are themselves objects with properties, they continue to be flattened with dot notation in the main field table (e.g., `specification.spec_fields`, `output.created_at`).

The key change: when flattening **stops** (at the depth limit, or when encountering an object/array-of-objects without inline-expandable properties), the type is a named schema reference instead of bare "object" or "array of object".

Rules for when to flatten vs. use a schema reference:
- **Flatten** (dot notation): Object has properties, depth < 2 (current behavior, unchanged).
- **Schema reference**: Object or array-of-objects where flattening would stop — either because of depth limit, or because the schema has no properties at the current resolution level, or because it's an array of objects (items are objects with properties).

This means the same schema might appear both flattened (in a parent's field table via dot notation) AND as a standalone schema (referenced by another endpoint or at a deeper level). That's fine — the goal is self-contained files.

### 4. Empty Request Bodies

Request bodies that currently show only `Content Type: application/json` with no field table (because the resolved schema has no properties) should now show the schema name if one is available. If the schema does have properties when properly resolved, they should appear.

If the request body genuinely has no known structure (e.g., accepts arbitrary JSON), keep the current behavior — just the content type, no field table.

## Schema Naming

### Named Schemas (from `$ref`)

Schemas originating from an OpenAPI `$ref` (e.g., `#/components/schemas/TaskMetadata`) use the schema's component name directly: `TaskMetadata`.

The resolver must preserve the original schema name when inlining `$ref` content. Implementation approach: add an `x-schema-name` property to the resolved schema dict so the parser can retrieve it.

### Inline Schemas (no `$ref`)

For objects defined inline (not via `$ref`), derive a name from the field name using PascalCase conversion:
- `questions_and_answers` → `QuestionAndAnswer` (singularized for array items)
- `task_metadata` → `TaskMetadata`
- `data_by_topic` → `DataByTopic`

Conversion rules:
- Split on underscores
- Capitalize each segment
- No singularization — use the field name as-is (these docs are consumed by agents, not humans)

### Conflict Resolution

When two different schemas would produce the same name:
1. Compare the schemas structurally (same properties, same types, same required fields).
2. If identical → reuse the same name and single schema definition. No conflict.
3. If different → append `V2`, `V3`, etc. to the later-encountered schema: `TaskMetadata`, `TaskMetadataV2`.

Comparison is per-endpoint (since each file is independent). Cross-file duplication is expected and desired.

## Edge Cases

### `oneOf`/`anyOf` with Object Variants

When a union type includes object variants, each object variant gets a schema entry:

| Field | Type | Description |
|-------|------|-------------|
| result | one of: SuccessResult, ErrorResult, null | The operation result |

Both `SuccessResult` and `ErrorResult` appear in the Schemas section.

For unions of only primitives (e.g., `one of: string, null`), no schema is needed — current behavior is fine.

### Objects Without Properties

Some OpenAPI schemas are typed as `object` but define no `properties` (e.g., free-form JSON, `additionalProperties: true`, or just `type: object`). These remain as `object` in the type column — no schema reference, since there's nothing to define.

### Circular References

Not a concern with this design. Schemas reference each other by name in a flat section, so `SchemaA` referencing `SchemaB` and vice versa is naturally representable.

### Deeply Nested Schemas

Schemas can reference other schemas to arbitrary depth. All transitively referenced schemas are included in the Schemas section. Since schemas are flat (not nested in the markdown), there's no depth limit concern.

### `allOf` Schemas

Continue merging `allOf` sub-schemas as today. If the merged result has an `x-schema-name` from one of the sub-schemas, use that name. Otherwise derive a name as for inline schemas.

## What Does NOT Change

- **SKILL.md generation**: The top-level skill file is unchanged.
- **CLI interface**: No new flags or arguments.
- **File naming**: Reference filenames remain the same.
- **Path/query parameter sections**: These don't involve complex objects.
- **Example JSON blocks**: Kept as-is when present.
- **Constraint handling**: Enums, formats, min/max — all unchanged.

## Out of Scope

- **Cross-file schema deduplication**: Each file is self-contained. We don't generate a shared schemas file.
- **Schema-only output mode**: No separate schema files or index.
- **Customization of naming strategy**: No CLI flags for schema naming conventions.
- **Markdown formatting changes**: Beyond adding the Schemas section, the overall doc structure stays the same.
