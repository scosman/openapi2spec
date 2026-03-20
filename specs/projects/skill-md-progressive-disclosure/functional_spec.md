---
status: complete
---

# Functional Spec: SKILL.md Progressive Disclosure

## Overview

Replace the monolithic endpoint table in SKILL.md with a 2-level structure: SKILL.md lists tags with links to per-tag files, and each per-tag file contains the endpoint table for that tag.

## Level 1: SKILL.md Tag Index

### Current Behavior

SKILL.md contains an `## API Reference` section with `### Tag Name` subsections, each containing a full endpoint table (Endpoint, Method, Name, Description, API Details URL).

### New Behavior

The `## API Reference` section becomes a tag index. For each tag, it shows:

- **Tag name** (as a heading or list item — not a table)
- **Tag description** (from the OpenAPI spec's top-level `tags[].description` field, if present)
- **Explicit file link** to the per-tag API list file (e.g., `reference/Projects_api_list.md`)

The file links must be written out literally in the markdown — not assembled by convention. Agents should be able to read the link directly from SKILL.md and follow it.

### Intro Text

The preamble (either default or user-provided) remains at the top. The default preamble's instruction text must be updated to describe the 2-level navigation: start with the tag list in SKILL.md, read the relevant tag file for endpoint details, then read per-endpoint reference files for full request/response schemas.

### Tag Ordering

Tags appear in the same order as today: first by the OpenAPI spec's top-level `tags` array, then any remaining tags in order of first encounter.

## Level 2: Per-Tag API List Files

### File Naming

Each tag gets a file named `{sanitized_tag_name}_api_list.md`. Sanitization rules:

- Lowercase the tag name
- Replace spaces with underscores
- Remove characters that aren't alphanumeric or underscores
- Example: `"Prompt Optimization"` → `prompt_optimization_api_list.md`
- Example: `"RAG/Search"` → `ragsearch_api_list.md`

### File Location

Per-tag API list files are written to the `reference/` directory alongside the existing per-endpoint reference files.

### File Content

Each per-tag file contains:

1. A heading with the tag name (e.g., `# Projects API`)
2. The tag description from the OpenAPI spec (if present)
3. The same endpoint table format currently used in SKILL.md:

```
| Endpoint | Method | Name | Description | API Details URL |
|----------|--------|------|-------------|-----------------|
| `/path` | GET | Name | Description... | reference/get_path.md |
```

Note: The `API Details URL` column links are relative to the SKILL.md location (i.e., `reference/filename.md`), keeping them consistent whether navigated from SKILL.md or from the tag file.

### Single-Tag Case

If the entire API has only one tag, still generate the 2-level structure. Consistency is more important than saving one level of indirection for small APIs.

## What Doesn't Change

- **Per-endpoint reference files**: Content, naming, and location are unchanged.
- **CLI interface**: Same `--spec`, `--preamble`, `--output` arguments. No new flags.
- **Preamble mechanism**: User-provided preambles still work. The default preamble text is updated but the `--preamble` override mechanism is the same.
- **Filename collision handling** for per-endpoint files: Unchanged.
- **Output directory structure**: Still timestamped subdirectories with `SKILL.md` and `reference/`.

## Edge Cases

### Tags with No Endpoints

Should not appear. Tags listed in the OpenAPI spec's top-level `tags` array but with zero matching endpoints are omitted from both SKILL.md and the per-tag files.

### "Other" Tag

Endpoints without explicit tags are grouped under "Other" (existing behavior). This generates an `other_api_list.md` file and an "Other" entry in the SKILL.md tag index, same as any other tag.

### Tag Name Collisions After Sanitization

If two tag names produce the same sanitized filename (e.g., "RAG Search" and "RAG/Search" both become `ragsearch_api_list.md`), append a numeric suffix: `ragsearch_api_list_2.md`. Follow the same collision handling pattern used for endpoint filenames.

### Empty Spec

If no endpoints are found, SKILL.md contains the preamble and an empty API Reference section (same as today). No per-tag files are generated.

## Example Output Structure

```
output/2026-03-20_143052/
  SKILL.md                          # Tag index with links
  reference/
    projects_api_list.md            # Per-tag endpoint table
    providers_api_list.md           # Per-tag endpoint table
    other_api_list.md               # Per-tag endpoint table
    get_api_projects.md             # Per-endpoint reference (unchanged)
    post_api_project.md             # Per-endpoint reference (unchanged)
    ...
```

## Example SKILL.md Content (Level 1)

```markdown
---
name: api-definition
description: Description of this API and when to use this skill.
---

This skill describes the endpoints and functionality of an API. Use the tag list
below to find the relevant API area, then read the linked file for a list of
endpoints. Each endpoint links to a detailed reference file with full
request/response details. You can call these APIs using curl or any HTTP client.

## API Reference

### Projects

Manage projects, including creation, updates, and deletion.

**Endpoints:** reference/projects_api_list.md

### Providers

Configure model providers and available models.

**Endpoints:** reference/providers_api_list.md
```
