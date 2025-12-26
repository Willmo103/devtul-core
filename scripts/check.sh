#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Resolve project root relative to this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

echo "=========================================="
echo "Running BLACK (Formatter)"
echo "=========================================="
uv run black .

echo ""
echo "=========================================="
echo "Running ISORT (Import Sorter)"
echo "=========================================="
uv run isort .

echo ""
echo "=========================================="
echo "Running PYTEST (Unit Tests & Coverage)"
echo "=========================================="
uv run pytest --cov=src --cov-report=html

echo ""
echo "=========================================="
echo "SUCCESS: All checks passed."
echo "Coverage report: htmlcov/index.html"
echo "=========================================="
