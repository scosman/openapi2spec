---
status: complete
---

# SKILL.md Progressive Disclosure (2-Level API Listing)

OpenAPI specs can be very large, resulting in a huge monolithic table in SKILL.md that forces agents to load all endpoint details even when they only need a subset. This project adds a level of indirection to enable progressive disclosure:

## Level 1: SKILL.md links to tags

The main SKILL.md file's API Reference section becomes a compact list of tags (API categories), each linking to a per-tag reference file. A short intro explains the structure and how to navigate it. This replaces the current flat endpoint table.

## Level 2: Per-tag API list files

Each tag gets its own file (e.g., `Projects_api_list.md`, `Providers_api_list.md`) containing the same endpoint table format currently used in SKILL.md — but scoped to just that tag's endpoints. These files live alongside the per-endpoint reference files.

This allows an agent to:
1. Read SKILL.md to see what API categories exist
2. Read only the relevant tag file(s) to find specific endpoints
3. Read per-endpoint reference files for full request/response details

The existing per-endpoint reference files (Level 3) remain unchanged.
