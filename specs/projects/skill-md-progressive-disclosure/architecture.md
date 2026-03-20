---
status: complete
---

# Architecture: SKILL.md Progressive Disclosure

## Scope

Modifications to 4 existing files in `openapi2skill/`. No new files or dependencies.

## Data Model Changes

### Tag Descriptions

`parser.group_by_tag()` currently returns `list[tuple[str, list[Endpoint]]]` (tag name + endpoints). It needs to also return the tag description from the OpenAPI spec's top-level `tags` array.

**Change:** Introduce a `TagGroup` dataclass in `models.py`:

```python
@dataclass
class TagGroup:
    name: str
    description: str  # empty string if not present in spec
    endpoints: list[Endpoint]
```

`group_by_tag()` return type changes from `list[tuple[str, list[Endpoint]]]` to `list[TagGroup]`.

No other model changes. `Endpoint`, `Parameter`, `RequestBody`, `Field`, `Response` are unchanged.

## Module Changes

### `models.py`

Add `TagGroup` dataclass as described above.

### `parser.py`

**`group_by_tag(endpoints, spec) -> list[TagGroup]`**

- Build a lookup dict from the spec's top-level `tags` array: `{tag_name: description}`.
- Return `TagGroup` objects instead of tuples, populating `description` from the lookup (empty string if tag has no description or isn't in the top-level array).
- Ordering logic unchanged: spec-defined tags first, then remaining in order of first encounter.

### `generator.py`

**`generate_skill_md(preamble, tag_groups, tag_filenames) -> str`** (signature changes)

The function now generates a tag index instead of endpoint tables. For each tag group:

```markdown
### {tag_name}

{tag_description if present}

**Endpoints:** reference/{tag_filename}
```

Parameters:
- `preamble: str` — unchanged
- `tag_groups: list[TagGroup]` — replaces `grouped_endpoints`
- `tag_filenames: dict[str, str]` — maps tag name to per-tag filename (replaces `filenames` which mapped endpoint keys to reference filenames)

**New: `generate_tag_api_list_md(tag_group, endpoint_filenames) -> str`**

Generates a per-tag API list file. Content:

```markdown
# {tag_name} API

{tag_description if present}

| Endpoint | Method | Name | Description | API Details URL |
|----------|--------|------|-------------|-----------------|
| `{path}` | {METHOD} | {name} | {description} | reference/{endpoint_filename} |
```

Parameters:
- `tag_group: TagGroup` — the tag and its endpoints
- `endpoint_filenames: dict[str, str]` — maps `"{method}_{path}"` to reference filename (same dict used today)

This is essentially the table-generation logic extracted from the current `generate_skill_md()`.

**`generate_reference_md(endpoint)` — unchanged.**

**`DEFAULT_PREAMBLE` — updated text:**

```
This skill describes the endpoints and functionality of an API. Use the tag list
below to find the relevant API area, then read the linked file for a list of
endpoints. Each endpoint links to a detailed reference file with full
request/response details. You can call these APIs using curl or any HTTP client.
```

**Helper functions** (`escape_table_cell`, `truncate_description`, `_get_status_description`) — unchanged.

### `writer.py`

**New: `generate_tag_filename(tag_name) -> str`**

Sanitizes a tag name into a filename:
1. Lowercase
2. Replace spaces with underscores
3. Remove characters that aren't `[a-z0-9_]`
4. Collapse multiple consecutive underscores into one
5. Strip leading/trailing underscores
6. Append `_api_list.md`

Example: `"Prompt Optimization"` → `"prompt_optimization_api_list.md"`

**New: `assign_tag_filenames(tag_groups) -> dict[str, str]`**

Maps tag name to filename. Uses `generate_tag_filename()` for each tag, with the same collision-handling pattern as `assign_filenames()`: if two tags produce the same filename, append `_2`, `_3`, etc.

Parameters:
- `tag_groups: list[TagGroup]`

Returns:
- `dict[str, str]` mapping tag name to filename

**`write_output(base_output_dir, skill_md, tag_api_lists, references) -> str`** (signature changes)

New parameter `tag_api_lists: list[tuple[str, str]]` — list of `(filename, content)` tuples for per-tag API list files. Written to `reference/` alongside endpoint reference files.

**`assign_filenames(endpoints)` and `generate_filename(method, path)` — unchanged.**

### `__main__.py`

Updated pipeline in `main()`:

```python
# (existing) Load, resolve, parse
spec = load_spec(args.spec)
spec = resolve_refs(spec)
endpoints = parse_endpoints(spec)

# (existing) Group by tag — now returns TagGroup objects
tag_groups = group_by_tag(endpoints, spec)

# (existing) Assign endpoint filenames
endpoint_filenames = assign_filenames(endpoints)

# (new) Assign tag filenames
tag_filenames = assign_tag_filenames(tag_groups)

# (existing) Load preamble
preamble = ...

# (changed) Generate SKILL.md — now tag index
skill_md = generate_skill_md(preamble, tag_groups, tag_filenames)

# (new) Generate per-tag API list files
tag_api_lists = []
for tag_group in tag_groups:
    filename = tag_filenames[tag_group.name]
    content = generate_tag_api_list_md(tag_group, endpoint_filenames)
    tag_api_lists.append((filename, content))

# (existing) Generate per-endpoint reference files
references = []
for endpoint in endpoints:
    ep_key = f"{endpoint.method}_{endpoint.path}"
    filename = endpoint_filenames.get(ep_key)
    if filename:
        content = generate_reference_md(endpoint)
        references.append((filename, content))

# (changed) Write output — now includes tag API lists
output_path = write_output(args.output, skill_md, tag_api_lists, references)
```

## Testing Strategy

Existing tests use `pytest`. The project has tests in `api_skill_generator/tests/`.

### Unit Tests

**`test_parser.py`**: Update `group_by_tag` tests to verify `TagGroup` objects are returned with correct `description` fields. Test cases:
- Tags with descriptions in spec
- Tags without descriptions
- Tags not in spec's top-level array (description = "")
- Ordering preserved

**`test_generator.py`**: 
- Update `generate_skill_md` tests to verify tag index format (headings, descriptions, file links — no endpoint tables)
- New tests for `generate_tag_api_list_md`: correct table format, description included when present, endpoint links use `reference/` prefix

**`test_writer.py`**:
- New tests for `generate_tag_filename`: sanitization rules, various inputs
- New tests for `assign_tag_filenames`: basic case, collision handling
- Update `write_output` tests to verify tag API list files are written to `reference/`

### No Integration Test Changes

The CLI arguments don't change, so any end-to-end test wiring stays the same.
