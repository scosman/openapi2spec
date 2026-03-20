"""CLI entry point for openapi2skill."""

import argparse
import sys
from pathlib import Path

from openapi2skill.generator import (
    DEFAULT_PREAMBLE,
    generate_reference_md,
    generate_skill_md,
    generate_tag_api_list_md,
)
from openapi2skill.loader import load_spec
from openapi2skill.parser import group_by_tag, parse_endpoints
from openapi2skill.resolver import resolve_refs
from openapi2skill.writer import assign_filenames, assign_tag_filenames, write_output


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate agent skills from OpenAPI specs",
        prog="openapi2skill",
    )
    parser.add_argument(
        "--spec",
        required=True,
        help="URL or file path to the OpenAPI JSON spec",
    )
    parser.add_argument(
        "--preamble",
        help="Path to a markdown file prepended to SKILL.md",
    )
    parser.add_argument(
        "--output",
        default="./output",
        help="Directory where the skill files are written (default: ./output)",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point.

    Exit codes:
        0: Success
        1: Failure (error printed to stderr)
    """
    args = parse_args()

    try:
        # Load and resolve spec
        spec = load_spec(args.spec)
        spec = resolve_refs(spec)

        # Parse endpoints
        endpoints = parse_endpoints(spec)

        # Warn on empty spec
        if not endpoints:
            print(
                "Warning: No endpoints found in spec",
                file=sys.stderr,
            )

        # Group by tag — now returns TagGroup objects
        tag_groups = group_by_tag(endpoints, spec)

        # Assign endpoint filenames
        endpoint_filenames = assign_filenames(endpoints)

        # Assign tag filenames
        tag_filenames = assign_tag_filenames(tag_groups)

        # Load preamble
        if args.preamble:
            preamble_path = Path(args.preamble)
            if not preamble_path.exists():
                print(
                    f"Error: Preamble file not found: {args.preamble}",
                    file=sys.stderr,
                )
                sys.exit(1)
            preamble = preamble_path.read_text()
        else:
            preamble = DEFAULT_PREAMBLE

        # Generate SKILL.md — now tag index
        skill_md = generate_skill_md(preamble, tag_groups, tag_filenames)

        # Generate per-tag API list files
        tag_api_lists: list[tuple[str, str]] = []
        for tag_group in tag_groups:
            filename = tag_filenames[tag_group.name]
            content = generate_tag_api_list_md(tag_group, endpoint_filenames)
            tag_api_lists.append((filename, content))

        # Generate per-endpoint reference files
        references: list[tuple[str, str]] = []
        for endpoint in endpoints:
            ep_key = f"{endpoint.method}_{endpoint.path}"
            filename = endpoint_filenames.get(ep_key)
            if filename:
                content = generate_reference_md(endpoint)
                references.append((filename, content))

        # Write output — now includes tag API lists
        output_path = write_output(args.output, skill_md, tag_api_lists, references)

        # Print output path to stdout
        print(f"Skill generated: {output_path}")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error: Failed to write output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
