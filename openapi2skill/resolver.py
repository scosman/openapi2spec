"""$ref resolver for OpenAPI specs."""

import copy


def resolve_refs(spec: dict) -> dict:
    """Resolve all $ref pointers in the spec, returning a fully-inlined copy.

    Args:
        spec: The OpenAPI spec dict

    Returns:
        A new dict with all $refs resolved in-place
    """
    resolved = copy.deepcopy(spec)

    def resolve_in_place(obj: dict | list, stack: set[str]) -> None:
        """Recursively walk and resolve $refs in place."""
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_path = obj["$ref"]
                if ref_path in stack:
                    obj.clear()
                    obj["type"] = "object"
                    obj["description"] = "(circular reference)"
                    if ref_path.startswith("#/components/schemas/"):
                        schema_name = ref_path.split("/")[-1]
                        obj["x-schema-name"] = schema_name
                    return

                # Get a fresh copy of the referenced content from original spec
                ref_content = _resolve_ref(spec, ref_path)
                if ref_content is not None:
                    # Make a deep copy so we can resolve refs within it without
                    # affecting the original or other references to same target
                    ref_copy = copy.deepcopy(ref_content)

                    # Resolve any nested refs in the copy
                    new_stack = stack | {ref_path}
                    resolve_in_place(ref_copy, new_stack)

                    obj.clear()
                    obj.update(ref_copy)
                    if ref_path.startswith("#/components/schemas/"):
                        schema_name = ref_path.split("/")[-1]
                        obj["x-schema-name"] = schema_name
            else:
                for value in obj.values():
                    resolve_in_place(value, stack)
        elif isinstance(obj, list):
            for item in obj:
                resolve_in_place(item, stack)

    resolve_in_place(resolved, set())
    return resolved


def _resolve_ref(spec: dict, ref: str) -> dict | None:
    """Resolve a $ref pointer to its target content.

    Args:
        spec: The original (unmodified) spec dict
        ref: Reference string like "#/components/schemas/User"

    Returns:
        The referenced dict, or None if not found
    """
    if not ref.startswith("#/"):
        return None

    parts = ref[2:].split("/")

    current = spec
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]

    return current if isinstance(current, dict) else None
