---
status: complete
---

# Implementation Plan: API Skill Generator

## Phases

- [x] Phase 1: Project setup, data model, and spec loading — Set up pyproject.toml with dependencies, create the dataclass models, implement `loader.py` and `resolver.py` with tests. This gives us a parsed, resolved OpenAPI spec dict to build on.
- [x] Phase 2: Parser — Implement `parser.py` (endpoint extraction, schema-to-fields conversion, tag grouping) with tests. After this phase, we can go from a raw spec to structured `Endpoint` objects.
- [x] Phase 3: Generators and writer — Implement `generator.py` (SKILL.md and reference markdown generation), `writer.py` (file naming, timestamped output, collision detection), and the CLI entry point in `main.py`. Includes the sample `preamble.md`, integration test, and all remaining unit tests.
