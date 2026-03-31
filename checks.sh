#!/usr/bin/env bash
set -euo pipefail

echo "=== Lint ==="
ruff check .

echo "=== Format ==="
ruff format --check .

echo "=== Test ==="
pytest

echo "=== Type check ==="
ty check .

echo "=== All checks passed ==="
