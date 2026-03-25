"""Tests for resolver.py."""

import copy

from openapi2skill import resolver


def test_resolve_simple_ref() -> None:
    """Test resolving a simple $ref."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {"schemas": {"User": {"type": "object", "properties": {}}}},
    }

    result = resolver.resolve_refs(spec)

    schema = result["paths"]["/users"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert "$ref" not in schema
    assert schema["type"] == "object"


def test_resolve_nested_refs() -> None:
    """Test resolving nested $refs."""
    spec = {
        "openapi": "3.0.0",
        "paths": {},
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {"address": {"$ref": "#/components/schemas/Address"}},
                },
                "Address": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                },
            }
        },
    }

    result = resolver.resolve_refs(spec)

    user_props = result["components"]["schemas"]["User"]["properties"]
    assert "$ref" not in user_props["address"]
    assert user_props["address"]["type"] == "object"
    assert "city" in user_props["address"]["properties"]


def test_resolve_circular_ref() -> None:
    """Test that circular references are handled gracefully.

    When a schema references itself (Node -> Node), the first level is resolved
    normally, but nested self-references become circular reference placeholders.
    """
    spec = {
        "openapi": "3.0.0",
        "paths": {},
        "components": {
            "schemas": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "parent": {"$ref": "#/components/schemas/Node"},
                    },
                }
            }
        },
    }

    result = resolver.resolve_refs(spec)

    node_props = result["components"]["schemas"]["Node"]["properties"]
    # First level parent is resolved (no longer a $ref)
    assert "$ref" not in node_props["parent"]
    assert node_props["parent"]["type"] == "object"

    # The nested parent inside the resolved parent should be a circular reference
    nested_parent = node_props["parent"]["properties"]["parent"]
    assert nested_parent["type"] == "object"
    assert nested_parent["description"] == "(circular reference)"


def test_resolve_does_not_mutate_input() -> None:
    """Test that the input spec is not mutated."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {"schemas": {"User": {"type": "object"}}},
    }

    original = copy.deepcopy(spec)
    resolver.resolve_refs(spec)

    assert spec == original


def test_resolve_invalid_ref_path() -> None:
    """Test handling of invalid $ref paths."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/nonexistent/path"}
                                }
                            }
                        }
                    }
                }
            }
        },
    }

    # Should not raise, just leave the ref unresolved
    result = resolver.resolve_refs(spec)

    # Invalid refs are left as-is since we only replace when resolution succeeds
    schema = result["paths"]["/users"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert schema["$ref"] == "#/nonexistent/path"


def test_resolve_external_ref_ignored() -> None:
    """Test that external refs are not resolved (left as-is)."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "https://example.com/schema"}
                                }
                            }
                        }
                    }
                }
            }
        },
    }

    result = resolver.resolve_refs(spec)

    schema = result["paths"]["/users"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert schema["$ref"] == "https://example.com/schema"


def test_resolve_refs_in_array() -> None:
    """Test resolving $refs inside arrays."""
    spec = {
        "openapi": "3.0.0",
        "paths": {},
        "components": {
            "schemas": {
                "UserList": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/User"},
                },
                "User": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        },
    }

    result = resolver.resolve_refs(spec)

    items = result["components"]["schemas"]["UserList"]["items"]
    assert "$ref" not in items
    assert items["type"] == "object"


def test_resolve_multiple_refs_same_target() -> None:
    """Test resolving multiple $refs pointing to the same target."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        }
                    }
                },
                "post": {
                    "responses": {
                        "201": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        }
                    }
                },
            }
        },
        "components": {"schemas": {"User": {"type": "object"}}},
    }

    result = resolver.resolve_refs(spec)

    get_schema = result["paths"]["/users"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    post_schema = result["paths"]["/users"]["post"]["responses"]["201"]["content"][
        "application/json"
    ]["schema"]

    assert "$ref" not in get_schema
    assert "$ref" not in post_schema
    assert get_schema["type"] == "object"
    assert post_schema["type"] == "object"


def test_resolve_deeply_nested_path() -> None:
    """Test resolving refs with deeply nested paths."""
    spec = {
        "openapi": "3.0.0",
        "paths": {},
        "components": {
            "schemas": {
                "Deep": {
                    "type": "object",
                    "properties": {
                        "nested": {
                            "type": "object",
                            "properties": {
                                "value": {"$ref": "#/components/schemas/Value"}
                            },
                        }
                    },
                },
                "Value": {"type": "string"},
            }
        },
    }

    result = resolver.resolve_refs(spec)

    deep_props = result["components"]["schemas"]["Deep"]["properties"]
    assert "$ref" not in deep_props["nested"]["properties"]["value"]
    assert deep_props["nested"]["properties"]["value"]["type"] == "string"


def test_resolve_sample_spec() -> None:
    """Test resolving the sample spec fixture."""
    import json
    from pathlib import Path

    fixture_path = Path(__file__).parent / "fixtures" / "sample_spec.json"
    spec = json.loads(fixture_path.read_text())

    result = resolver.resolve_refs(spec)

    # Check that User $ref in paths is resolved
    user_schema = result["paths"]["/users"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert "$ref" not in user_schema
    assert user_schema["type"] == "array"

    # Check nested Address ref in User schema is resolved
    user_props = result["components"]["schemas"]["User"]["properties"]
    assert "$ref" not in user_props["address"]
    assert user_props["address"]["type"] == "object"


def test_resolve_ref_preserves_schema_name() -> None:
    """Test that x-schema-name is added when resolving a #/components/schemas/X ref."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {"schemas": {"User": {"type": "object", "properties": {}}}},
    }

    result = resolver.resolve_refs(spec)

    schema = result["paths"]["/users"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert schema["x-schema-name"] == "User"


def test_resolve_ref_no_schema_name_for_non_schema_ref() -> None:
    """Test that x-schema-name is NOT added for non-schema refs."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "parameters": [{"$ref": "#/components/parameters/UserId"}],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
        "components": {"parameters": {"UserId": {"name": "id", "in": "query"}}},
    }

    result = resolver.resolve_refs(spec)

    param = result["paths"]["/users"]["get"]["parameters"][0]
    assert "x-schema-name" not in param


def test_resolve_circular_ref_preserves_schema_name() -> None:
    """Test that circular ref placeholder gets x-schema-name."""
    spec = {
        "openapi": "3.0.0",
        "paths": {},
        "components": {
            "schemas": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "parent": {"$ref": "#/components/schemas/Node"},
                    },
                }
            }
        },
    }

    result = resolver.resolve_refs(spec)

    node_props = result["components"]["schemas"]["Node"]["properties"]
    nested_parent = node_props["parent"]["properties"]["parent"]
    assert nested_parent["type"] == "object"
    assert nested_parent["description"] == "(circular reference)"
    assert nested_parent["x-schema-name"] == "Node"
