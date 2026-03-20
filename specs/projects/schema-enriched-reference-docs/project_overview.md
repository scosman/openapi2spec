---
status: complete
---

# Schema-Enriched Reference Docs

The `openapi2skill` tool generates per-endpoint API reference markdown files. Currently, when a field's type is a complex object or array of objects, the docs just say "object" or "array of object" — leaving out the structure of those objects entirely. This means an agent (or developer) reading a single reference file can't understand how to construct a valid request or interpret a response without looking elsewhere.

## Goals

- Add a **Schemas** section to each reference file that lists the schemas of all complex objects used by that endpoint (request body fields, response fields).
- Inline schema references: instead of "array of objects" or "object", the field table says the exact schema name (e.g., `array of QuestionAnswer`, `TaskMetadata`).
- Nested schemas are included: if Schema A has a field of type Schema B, both schemas appear in the Schemas section.
- Duplication is intentional: the same schema may appear in many endpoint reference files. The design goal is that a single file is fully self-contained — everything needed to build a request and understand the response is in that one file.

## Context

- The tool reads an OpenAPI 3.x JSON spec as input.
- `$ref` references are resolved before parsing, so the original schema names (from `#/components/schemas/...`) are available during resolution but currently discarded.
- The parser flattens nested objects with dot notation up to 3 levels deep, and beyond that just says "object".
- Request bodies with no properties currently produce an empty body section (just the content type header).

## Examples of Current Problems

1. **Empty request body**: `PATCH /api/projects/{project_id}/tasks/{task_id}/runs/{run_id}` shows `Request Body: Content Type: application/json` with no field table at all.
2. **"array of object" with no schema**: `POST /api/copilot/refine_spec_with_question_answers` has fields like `questions_and_answers: array of object` and responses like `new_proposed_spec_edits: array of object` with no description of what those objects contain.
3. **Opaque nested objects**: `POST /api/copilot/generate_batch` has `sdg_session_config.topic_generation_config.task_metadata: object` described as "Metadata about the model used for a task" but no field breakdown.
