"""Tests for loader.py."""

import json
from pathlib import Path
from unittest import mock

import httpx
import pytest

from openapi2skill import loader


def test_load_spec_from_file(tmp_path: Path) -> None:
    """Test loading a valid spec from a file path."""
    spec_content = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
    }
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(spec_content))

    result = loader.load_spec(str(spec_file))

    assert result == spec_content


def test_load_spec_file_not_found() -> None:
    """Test that loading a non-existent file raises ValueError."""
    with pytest.raises(ValueError, match="File not found"):
        loader.load_spec("/nonexistent/path/spec.json")


def test_load_spec_invalid_json(tmp_path: Path) -> None:
    """Test that invalid JSON raises ValueError."""
    spec_file = tmp_path / "invalid.json"
    spec_file.write_text("not valid json {{{")

    with pytest.raises(ValueError, match="invalid JSON"):
        loader.load_spec(str(spec_file))


def test_load_spec_missing_openapi_key(tmp_path: Path) -> None:
    """Test that missing 'openapi' key raises ValueError."""
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps({"paths": {}}))

    with pytest.raises(ValueError, match="missing 'openapi' key"):
        loader.load_spec(str(spec_file))


def test_load_spec_missing_paths_key(tmp_path: Path) -> None:
    """Test that missing 'paths' key raises ValueError."""
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps({"openapi": "3.0.0"}))

    with pytest.raises(ValueError, match="missing 'paths' key"):
        loader.load_spec(str(spec_file))


def test_load_spec_not_a_dict(tmp_path: Path) -> None:
    """Test that non-object JSON raises ValueError."""
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(["not", "a", "dict"]))

    with pytest.raises(ValueError, match="expected a JSON object"):
        loader.load_spec(str(spec_file))


def test_load_spec_from_url() -> None:
    """Test loading a valid spec from a URL."""
    spec_content = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
    }
    mock_response = mock.Mock()
    mock_response.text = json.dumps(spec_content)
    mock_response.raise_for_status = mock.Mock()

    with mock.patch.object(httpx, "get", return_value=mock_response) as mock_get:
        result = loader.load_spec("https://example.com/spec.json")

    mock_get.assert_called_once()
    assert result == spec_content


def test_load_spec_url_http_error() -> None:
    """Test that HTTP errors are properly wrapped."""
    mock_response = mock.Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=mock.Mock(), response=mock_response
    )

    with mock.patch.object(httpx, "get", return_value=mock_response):
        with pytest.raises(ValueError, match="HTTP 404"):
            loader.load_spec("https://example.com/spec.json")


def test_load_spec_url_network_error() -> None:
    """Test that network errors are properly wrapped."""
    with mock.patch.object(
        httpx, "get", side_effect=httpx.RequestError("Connection refused")
    ):
        with pytest.raises(ValueError, match="Failed to fetch OpenAPI spec"):
            loader.load_spec("https://example.com/spec.json")


def test_load_spec_url_invalid_json() -> None:
    """Test that invalid JSON from URL raises ValueError."""
    mock_response = mock.Mock()
    mock_response.text = "not valid json"
    mock_response.raise_for_status = mock.Mock()

    with mock.patch.object(httpx, "get", return_value=mock_response):
        with pytest.raises(ValueError, match="invalid JSON"):
            loader.load_spec("https://example.com/spec.json")


def test_load_spec_http_url() -> None:
    """Test that http:// URLs are also supported."""
    spec_content = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
    }
    mock_response = mock.Mock()
    mock_response.text = json.dumps(spec_content)
    mock_response.raise_for_status = mock.Mock()

    with mock.patch.object(httpx, "get", return_value=mock_response) as mock_get:
        result = loader.load_spec("http://example.com/spec.json")

    mock_get.assert_called_once()
    assert result == spec_content


def test_load_spec_uses_timeout() -> None:
    """Test that the loader uses a reasonable timeout."""
    spec_content = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
    }
    mock_response = mock.Mock()
    mock_response.text = json.dumps(spec_content)
    mock_response.raise_for_status = mock.Mock()

    with mock.patch.object(httpx, "get", return_value=mock_response) as mock_get:
        loader.load_spec("https://example.com/spec.json")

    call_kwargs = mock_get.call_args[1]
    assert "timeout" in call_kwargs
    assert call_kwargs["timeout"] == 10.0


def test_load_spec_follows_redirects() -> None:
    """Test that the loader follows redirects."""
    spec_content = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
    }
    mock_response = mock.Mock()
    mock_response.text = json.dumps(spec_content)
    mock_response.raise_for_status = mock.Mock()

    with mock.patch.object(httpx, "get", return_value=mock_response) as mock_get:
        loader.load_spec("https://example.com/spec.json")

    call_kwargs = mock_get.call_args[1]
    assert call_kwargs.get("follow_redirects") is True
