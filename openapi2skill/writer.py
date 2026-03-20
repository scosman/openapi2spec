"""Output writer - handles file naming, timestamps, and file writing."""

import re
import sys
from datetime import datetime
from pathlib import Path


def generate_filename(method: str, path: str) -> str:
    """Generate a reference filename from method and path.

    Args:
        method: HTTP method (e.g., "GET", "POST")
        path: URL path (e.g., "/users/{id}")

    Returns:
        Filename like "get_users_id.md"

    Examples:
        >>> generate_filename("GET", "/users")
        'get_users.md'
        >>> generate_filename("POST", "/api/users/{id}/roles")
        'post_api_users_id_roles.md'
    """
    # Lowercase method
    filename = method.lower()

    # Process path segments
    # Strip leading slash and split
    path_clean = path.lstrip("/").lower()

    # Replace path parameter braces: {id} -> id
    path_clean = re.sub(r"\{([^}]+)\}", r"\1", path_clean)

    # Split on / and join with _
    if path_clean:
        segments = path_clean.split("/")
        filename += "_" + "_".join(segments)

    return f"{filename}.md"


def assign_filenames(endpoints: list) -> dict[str, str]:
    """Assign unique filenames to endpoints.

    Args:
        endpoints: List of Endpoint objects

    Returns:
        Dict mapping "{method}_{path}" to filename
    """
    filenames: dict[str, str] = {}
    used_names: dict[str, int] = {}  # Track count of each base name

    for endpoint in endpoints:
        ep_key = f"{endpoint.method}_{endpoint.path}"
        base_name = generate_filename(endpoint.method, endpoint.path)

        if base_name in used_names:
            # Collision detected - increment counter
            used_names[base_name] += 1
            # Remove .md extension, add suffix, re-add extension
            name_without_ext = base_name[:-3]
            final_name = f"{name_without_ext}_{used_names[base_name]}.md"
            print(
                f"Warning: filename collision for {ep_key}, using {final_name}",
                file=sys.stderr,
            )
        else:
            used_names[base_name] = 1
            final_name = base_name

        filenames[ep_key] = final_name

    return filenames


def generate_tag_filename(tag_name: str) -> str:
    """Generate a per-tag API list filename from tag name.

    Args:
        tag_name: The tag name (e.g., "Prompt Optimization")

    Returns:
        Filename like "prompt_optimization_api_list.md"

    Examples:
        >>> generate_tag_filename("Projects")
        'projects_api_list.md'
        >>> generate_tag_filename("Prompt Optimization")
        'prompt_optimization_api_list.md'
        >>> generate_tag_filename("RAG/Search")
        'ragsearch_api_list.md'
    """
    # Lowercase
    filename = tag_name.lower()

    # Replace spaces with underscores
    filename = filename.replace(" ", "_")

    # Remove characters that aren't alphanumeric or underscores
    filename = re.sub(r"[^a-z0-9_]", "", filename)

    # Collapse multiple consecutive underscores into one
    filename = re.sub(r"_+", "_", filename)

    # Strip leading/trailing underscores
    filename = filename.strip("_")

    # Append suffix
    return f"{filename}_api_list.md"


def assign_tag_filenames(tag_groups: list) -> dict[str, str]:
    """Assign unique filenames to tag groups.

    Args:
        tag_groups: List of TagGroup objects

    Returns:
        Dict mapping tag name to filename
    """
    filenames: dict[str, str] = {}
    used_names: dict[str, int] = {}  # Track count of each base name

    for tag_group in tag_groups:
        base_name = generate_tag_filename(tag_group.name)

        if base_name in used_names:
            # Collision detected - increment counter
            used_names[base_name] += 1
            # Remove .md extension, add suffix, re-add extension
            name_without_ext = base_name[:-3]
            final_name = f"{name_without_ext}_{used_names[base_name]}.md"
            print(
                f"Warning: tag filename collision for '{tag_group.name}', using {final_name}",
                file=sys.stderr,
            )
        else:
            used_names[base_name] = 1
            final_name = base_name

        filenames[tag_group.name] = final_name

    return filenames


def write_output(
    base_output_dir: str,
    skill_md: str,
    tag_api_lists: list[tuple[str, str]],
    references: list[tuple[str, str]],
) -> str:
    """Write all output files.

    Args:
        base_output_dir: Base output directory (e.g., "./output")
        skill_md: SKILL.md content
        tag_api_lists: List of (filename, content) tuples for per-tag API list files
        references: List of (filename, content) tuples for endpoint reference files

    Returns:
        Path to the created timestamped directory

    Raises:
        OSError: On write failure
    """
    base_path = Path(base_output_dir)

    # Create timestamped subdirectory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_path = base_path / timestamp
    output_path.mkdir(parents=True, exist_ok=True)

    # Create reference subdirectory
    reference_path = output_path / "reference"
    reference_path.mkdir(exist_ok=True)

    # Write SKILL.md
    skill_file = output_path / "SKILL.md"
    skill_file.write_text(skill_md)

    # Write tag API list files
    for filename, content in tag_api_lists:
        tag_file = reference_path / filename
        tag_file.write_text(content)

    # Write endpoint reference files
    for filename, content in references:
        ref_file = reference_path / filename
        ref_file.write_text(content)

    return str(output_path)
