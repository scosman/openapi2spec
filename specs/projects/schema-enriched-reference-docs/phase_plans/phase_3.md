---
status: complete
---

# Phase 3: Generator + Integration

## Overview

Add `_generate_schemas_section` to `generator.py`, call it from `generate_reference_md`. Update integration test. Run against the sample spec and verify output.

## Steps

### 1. Add `_generate_schemas_section` to `generator.py`

**File:** `openapi2skill/generator.py`

**Add import:** Import `Schema` from models.

```python
from openapi2skill.models import Endpoint, Schema, TagGroup
```

**Add function after `_get_status_description`:**

```python
def _generate_schemas_section(schemas: list[Schema]) -> list[str]:
    """Generate markdown lines for the Schemas section.
    
    Args:
        schemas: List of Schema objects to render
        
    Returns:
        List of markdown lines for the Schemas section
    """
    lines: list[str] = []
    
    lines.append("## Schemas")
    lines.append("")
    
    for schema in schemas:
        lines.append(f"### {schema.name}")
        lines.append("")
        
        if schema.description:
            lines.append(schema.description)
            lines.append("")
        
        lines.append("| Field | Type | Required | Description |")
        lines.append("|-------|------|----------|-------------|")
        
        for field in schema.fields:
            desc = field.description
            if field.constraints:
                if desc:
                    desc = f"{desc}. {field.constraints}"
                else:
                    desc = field.constraints
            lines.append(
                f"| {field.name} | {field.type} | {'Yes' if field.required else 'No'} | {desc} |"
            )
        
        lines.append("")
    
    return lines
```

### 2. Modify `generate_reference_md` to include Schemas section

**File:** `openapi2skill/generator.py`

**Add at the end of `generate_reference_md`, before the return:**

```python
    # Schemas section
    if endpoint.schemas:
        lines.extend(_generate_schemas_section(endpoint.schemas))

    return "\n".join(lines)
```

### 3. Update integration test

**File:** `tests/test_integration.py`

**Add test:** `test_pipeline_with_schemas_section` - verify schemas appear in generated reference files

**Update existing test:** `test_full_pipeline_with_sample_spec` - verify schemas section is present for endpoints with complex objects

### 4. Update test fixtures if needed

**File:** `tests/fixtures/sample_spec.json`

The existing spec already has `Address` referenced from `User` and arrays of objects, which should trigger schema collection.

## Tests

### test_generator.py — New tests

1. `test_generate_schemas_section_empty`: Empty schemas list -> empty output
2. `test_generate_schemas_section_single`: Single schema -> correct markdown
3. `test_generate_schemas_section_multiple`: Multiple schemas -> all rendered
4. `test_generate_schemas_section_with_description`: Schema with description -> description included
5. `test_generate_schemas_section_with_constraints`: Field with constraints -> constraints in description
6. `test_reference_md_with_schemas`: Endpoint with schemas -> Schemas section rendered at end
7. `test_reference_md_no_schemas`: Endpoint without schemas -> no Schemas section

### test_integration.py — New/updated tests

1. `test_pipeline_includes_schemas_section`: Verify generated reference files include Schemas sections where expected

## Verification

- Run `uv run ruff check .` — lint clean
- Run `uv run ruff format .` — format clean
- Run `uv run pytest` — all tests pass
- Verify sample spec output has Schemas section with Address schema
