"""Tests for __main__.py CLI."""

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from openapi2skill import __main__


def test_main_success(tmp_path: Path) -> None:
    """Test full pipeline runs successfully."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(spec))
    output_dir = tmp_path / "output"

    with mock.patch.object(
        sys,
        "argv",
        ["openapi2skill", "--spec", str(spec_file), "--output", str(output_dir)],
    ):
        __main__.main()

    # Check output directory was created
    assert output_dir.exists()
    subdirs = list(output_dir.iterdir())
    assert len(subdirs) == 1
    assert (subdirs[0] / "SKILL.md").exists()
    assert (subdirs[0] / "reference").exists()


def test_main_with_preamble_file(tmp_path: Path) -> None:
    """Test custom preamble is loaded and used."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(spec))

    preamble_file = tmp_path / "preamble.md"
    preamble_file.write_text("# Custom API\n\nThis is a custom preamble.")

    output_dir = tmp_path / "output"

    with mock.patch.object(
        sys,
        "argv",
        [
            "openapi2skill",
            "--spec",
            str(spec_file),
            "--preamble",
            str(preamble_file),
            "--output",
            str(output_dir),
        ],
    ):
        __main__.main()

    # Check custom preamble is in SKILL.md
    subdirs = list(output_dir.iterdir())
    skill_md = (subdirs[0] / "SKILL.md").read_text()
    assert "# Custom API" in skill_md
    assert "This is a custom preamble." in skill_md


def test_main_missing_spec_file(tmp_path: Path) -> None:
    """Test error on missing spec file."""
    output_dir = tmp_path / "output"

    with mock.patch.object(
        sys,
        "argv",
        [
            "openapi2skill",
            "--spec",
            str(tmp_path / "nonexistent.json"),
            "--output",
            str(output_dir),
        ],
    ):
        with pytest.raises(SystemExit) as exc_info:
            __main__.main()

        assert exc_info.value.code == 1


def test_main_invalid_spec(tmp_path: Path) -> None:
    """Test error on invalid spec."""
    spec_file = tmp_path / "invalid.json"
    spec_file.write_text("not valid json")
    output_dir = tmp_path / "output"

    with mock.patch.object(
        sys,
        "argv",
        ["openapi2skill", "--spec", str(spec_file), "--output", str(output_dir)],
    ):
        with pytest.raises(SystemExit) as exc_info:
            __main__.main()

        assert exc_info.value.code == 1


def test_main_missing_preamble_file(tmp_path: Path) -> None:
    """Test error on missing preamble file."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
    }
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(spec))
    output_dir = tmp_path / "output"

    with mock.patch.object(
        sys,
        "argv",
        [
            "openapi2skill",
            "--spec",
            str(spec_file),
            "--preamble",
            str(tmp_path / "missing.md"),
            "--output",
            str(output_dir),
        ],
    ):
        with pytest.raises(SystemExit) as exc_info:
            __main__.main()

        assert exc_info.value.code == 1


def test_main_output_printed(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test output path is printed to stdout."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
    }
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(spec))
    output_dir = tmp_path / "output"

    with mock.patch.object(
        sys,
        "argv",
        ["openapi2skill", "--spec", str(spec_file), "--output", str(output_dir)],
    ):
        __main__.main()

    captured = capsys.readouterr()
    assert "Skill generated:" in captured.out
    assert str(output_dir) in captured.out


def test_main_empty_spec_warning(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Test warning printed for empty spec."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
    }
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(spec))
    output_dir = tmp_path / "output"

    with mock.patch.object(
        sys,
        "argv",
        ["openapi2skill", "--spec", str(spec_file), "--output", str(output_dir)],
    ):
        __main__.main()

    captured = capsys.readouterr()
    assert "Warning: No endpoints found in spec" in captured.err


def test_main_default_output_dir(tmp_path: Path) -> None:
    """Test default output directory is ./output."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
    }
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(spec))

    # Change to temp directory so output is written there
    original_cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)

        with mock.patch.object(
            sys, "argv", ["openapi2skill", "--spec", str(spec_file)]
        ):
            __main__.main()

        assert (tmp_path / "output").exists()
    finally:
        os.chdir(original_cwd)


def test_main_missing_required_spec_arg() -> None:
    """Test error when --spec is not provided."""
    with mock.patch.object(sys, "argv", ["openapi2skill"]):
        with pytest.raises(SystemExit) as exc_info:
            __main__.main()

        assert exc_info.value.code != 0


def test_main_uses_default_preamble(tmp_path: Path) -> None:
    """Test that default preamble is used when --preamble not provided."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
    }
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(spec))
    output_dir = tmp_path / "output"

    with mock.patch.object(
        sys,
        "argv",
        ["openapi2skill", "--spec", str(spec_file), "--output", str(output_dir)],
    ):
        __main__.main()

    # Check default preamble content is in SKILL.md
    subdirs = list(output_dir.iterdir())
    skill_md = (subdirs[0] / "SKILL.md").read_text()
    assert "curl" in skill_md


def test_main_via_subprocess(tmp_path: Path) -> None:
    """Test running the CLI as a subprocess (end-to-end test)."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(spec))
    output_dir = tmp_path / "output"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "openapi2skill",
            "--spec",
            str(spec_file),
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    assert result.returncode == 0
    assert "Skill generated:" in result.stdout
