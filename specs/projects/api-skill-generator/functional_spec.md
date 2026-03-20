---
status: complete
---

# Functional Spec: API Skill Generator

## Overview

A CLI tool that reads an OpenAPI 3.x spec and generates an agent skill (agentskills.io format) so AI agents can discover and call the API using HTTP tools like curl.

## CLI Interface

```
uv run openapi2skill [OPTIONS]
```

### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--spec` | string | **(required)** | URL or file path to the OpenAPI JSON spec |
| `--preamble` | string | (none — uses built-in default) | Path to a markdown file prepended to SKILL.md |
| `--output` | string | `./output` | Directory where the skill files are written |

### Behavior

- If `--spec` starts with `http://` or `https://`, fetch it over HTTP
- If `--spec` is a file path, read from disk
- Each run creates a new timestamped subdirectory inside the output directory (e.g. `output/2026-03-19_143052/`). Format: `YYYY-MM-DD_HHMMSS`. This avoids overwriting previous runs.
- The output directory and subdirectory are created if they don't exist
- Exit code 0 on success, non-zero on failure with a descriptive error message to stderr

## Output Structure

Given an API with endpoints, the generator produces:

```
output/
  2026-03-19_143052/
    SKILL.md
    reference/
      get_users.md
      post_users.md
      get_users_by_id.md
      ...
```

### SKILL.md Format

```markdown
[Preamble content — verbatim from the preamble file]

## API Reference

### [Tag Name]

| Endpoint | Method | Name | Description |
|----------|--------|------|-------------|
| `/api/users` | GET | List Users | Returns all users | [Details](reference/get_users.md) |
| `/api/users` | POST | Create User | Creates a new user | [Details](reference/post_users.md) |

### [Another Tag]

| Endpoint | Method | Name | Description |
|----------|--------|------|-------------|
| ... | ... | ... | ... |
```

**Grouping rules:**
- Endpoints are grouped by their first OpenAPI tag
- If an endpoint has multiple tags, it appears under the first tag only
- Endpoints with no tag are grouped under "Other"
- Tags are ordered as they appear in the spec's top-level `tags` array; any tags not listed there appear at the end in order of first encounter

**Table columns:**
- **Endpoint**: The URL path (e.g. `/api/users/{id}`)
- **Method**: HTTP method, uppercase (GET, POST, PUT, DELETE, PATCH)
- **Name**: The `summary` field from the operation, or the `operationId` if no summary exists
- **Description**: The `description` field from the operation, truncated to ~100 chars with "..." if longer
- **Details**: Link to the per-endpoint reference file

**Escaping:** Name and Description values must be escaped for markdown table safety — pipe characters (`|`), newlines, and other table-breaking characters are escaped or replaced.

### Reference File Naming

Each endpoint gets a file named by its method and path:

- Lowercase method prefix: `get_`, `post_`, `put_`, `delete_`, `patch_`
- Path segments joined with `_`, stripping leading slash
- Path parameters keep their name without braces: `{id}` becomes `id`
- Example: `POST /api/users/{id}/roles` → `post_api_users_id_roles.md`

### Reference File Format

Each file contains full API documentation for one endpoint:

```markdown
# [Name]

**[METHOD] [path]**

[Full description from the spec]

## Request

### Path Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| id | integer | Yes | The user ID |

### Query Parameters

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| limit | integer | No | 20 | Max results |

### Request Body

**Content Type:** `application/json`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | User's name |
| email | string | Yes | Email address |
| role | string | No | One of: admin, user. Default: user |

#### Example

```json
{
  "name": "Alice",
  "email": "alice@example.com"
}
```

## Responses

### 200 OK

[Description if provided]

| Field | Type | Description |
|-------|------|-------------|
| id | integer | User ID |
| name | string | User's name |

#### Example

```json
{
  "id": 1,
  "name": "Alice"
}
```

### 422 Validation Error

[Standard FastAPI validation error format]

### 500 Internal Server Error

[Description if provided]
```

**Section inclusion rules:**
- Only include sections that have content (e.g., skip "Path Parameters" if there are none)
- Nested objects: flatten with dot notation (e.g. `address.street`) or show as nested tables — whichever is clearer for the specific schema
- Arrays: show the item type (e.g. `array of string`, `array of User`)
- Enums: list values inline (e.g. "One of: admin, user, guest")
- Examples: include if present in the OpenAPI spec; omit the example section if not

## Input Handling

### OpenAPI Spec

- Supports OpenAPI 3.0 and 3.1 JSON format
- Fetches from URL or reads from file based on scheme detection
- If the spec cannot be loaded or parsed, exit with a clear error message
- Validates that the loaded JSON has the expected OpenAPI structure (has `openapi` and `paths` fields at minimum)

### Preamble File

- Read as raw text/markdown and inserted verbatim at the top of SKILL.md
- If the file doesn't exist, exit with an error

## Edge Cases

- **Empty spec (no paths):** Generate a SKILL.md with just the preamble and an empty API Reference section. Print a warning to stderr.
- **Missing summary/description on an endpoint:** Use operationId for the name; leave description blank in the table
- **Missing operationId, summary, and description:** Use the method + path as the name (e.g. "GET /api/users")
- **Extremely long descriptions in reference files:** Include the full text — these files are only loaded on demand by agents following a link
- **Duplicate generated filenames:** Append `_2`, `_3` etc. if a collision is detected (unlikely but possible if paths differ only by casing or special chars). Log a warning to stderr when this happens.
- **`$ref` in schemas:** Resolve `$ref` references within the spec before generating. OpenAPI specs commonly use `$ref` to point to `#/components/schemas/...`

## Out of Scope

- Authentication / security scheme handling
- OpenAPI 2.0 (Swagger) support
- YAML OpenAPI specs (JSON only)
- Generating code or curl commands — agents can construct these from the reference docs
- Watching for spec changes / incremental regeneration
- Interactive mode

## Default Preamble

When no `--preamble` is provided, the generator uses a built-in generic preamble:

> This skill describes the endpoints and functionality of an API. Use the summary table below to find relevant endpoints, then read the linked reference files for full request/response details. You can call these APIs using curl or any HTTP client.

This is embedded as a string constant in the code (not a separate file), keeping the tool self-contained.
