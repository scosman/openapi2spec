# openapi2skill

Generate agent skills from OpenAPI specs. Creates [agentskills.io](https://agentskills.io) format documentation so AI agents can discover and call your API.

## Installation

```bash
uv sync
```

## Usage

```bash
uv run openapi2skill --spec <url-or-file> [--preamble <file>] [--output <dir>]
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--spec` | Yes | - | URL or file path to the OpenAPI JSON spec |
| `--preamble` | No | Built-in default | Path to a markdown file prepended to SKILL.md |
| `--output` | No | `./output` | Directory where skill files are written |

### Examples

From a URL:
```bash
uv run openapi2skill --spec https://api.example.com/openapi.json
```

From a local file:
```bash
uv run openapi2skill --spec ./openapi.json --output ./docs
```

With a custom preamble:
```bash
uv run openapi2skill --spec ./openapi.json --preamble ./preamble.md
```

## Output Structure

Each run creates a timestamped subdirectory:

```
output/
  2026-03-19_143052/
    SKILL.md
    reference/
      get_users.md
      post_users.md
      get_users_id.md
      ...
```

### SKILL.md

Contains a summary table of all endpoints grouped by tag, with links to detailed reference files.

### Reference Files

Each endpoint gets a detailed markdown file with:
- Path and query parameters
- Request body schema with field types and constraints
- Response schemas for each status code
- Examples (when available in the spec)

## Requirements

- Python 3.13+
- OpenAPI 3.x JSON spec (YAML not supported)

## Development

Run tests:
```bash
uv run pytest
```

Lint and format:
```bash
uv run ruff check .
uv run ruff format .
```
