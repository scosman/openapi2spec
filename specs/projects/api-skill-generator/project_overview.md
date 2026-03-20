---
status: complete
---

# Dynamic Agent Skill Builder from OpenAPI Spec

## What It Does

A generator that takes an OpenAPI spec (from a FastAPI server or any OpenAPI JSON file) and produces an agent skill (https://agentskills.io) that describes the API so that an AI agent can call it using tools like curl or similar HTTP clients.

This is **not** an MCP wrapper — it's a descriptive skill that teaches an agent about the API's capabilities, endpoints, request/response formats, and how to interact with it.

## Who It's For

Developers who run API servers (particularly FastAPI-based) and want AI agents to be able to discover and use their APIs without needing a dedicated MCP integration.

## Why

MCP wrappers are heavyweight. Many APIs already have OpenAPI specs, and AI agents are capable of making HTTP calls directly. A well-structured skill file gives agents everything they need to understand and call the API — no extra runtime layer required.

## Design

### Output Structure

The generator produces a skill with two parts:

**1. SKILL.md (main skill file)**

- **Section 1: Preamble** — A static markdown description of the API, passed in by the user. Provides context about what the API is, how to authenticate, base URL, etc.
- **Section 2: API Table** — A table listing every API endpoint with columns:
  - URL Path (e.g. `/api/create_user`)
  - HTTP Method (POST, GET, etc.)
  - Name
  - Description
  - Link to detailed reference file (e.g. `reference/post_create_user.md`)

**2. Per-endpoint reference files (in `reference/` directory)**

Each API endpoint gets a detailed reference file (e.g. `reference/post_create_user.md`) containing:

- Name
- Description
- Request body: each parameter, schema, required/optional, types, constraints
- Response schemas for each status code (200, 422, 500, etc.)

These should be maximally detailed — equivalent to what Scalar or Swagger UI would show.

## Technical Requirements

- **CLI tool** run via `uv run ...`
- **Input: OpenAPI spec** — Accepts a file path or URL to an `openapi.json` (required, no default)
- **Input: Preamble file** — Optional path to a markdown/text file for the preamble. Falls back to a built-in generic preamble if not provided.
- **Language**: Python (project already initialized with pyproject.toml)
- **Output**: Writes SKILL.md and reference files to a specified output directory
- **OpenAPI version**: 3.0/3.1 only (modern FastAPI)
- **No auth handling** — authentication is out of scope
- **Examples**: Include request/response examples from the spec when available
- **Grouping**: Endpoints grouped by tag in the API table
