#!/usr/bin/env fish

# Resolve project root relative to this script
set script_dir (realpath (dirname (status --current-filename)))
set project_root "$script_dir/.."
cd $project_root

echo "=========================================="
echo "Running BLACK (Formatter)"
echo "=========================================="
uv run black .
or begin; echo "Black failed"; exit 1; end

echo ""
echo "=========================================="
echo "Running ISORT (Import Sorter)"
echo "=========================================="
uv run isort .
or begin; echo "Isort failed"; exit 1; end

echo ""
echo "=========================================="
echo "Running PYTEST (Unit Tests & Coverage)"
echo "=========================================="
uv run pytest --cov=src --cov-report=html
or begin; echo "Pytest failed"; exit 1; end

echo ""
echo "=========================================="
echo "SUCCESS: All checks passed."
echo "Coverage report: htmlcov/index.html"
echo "=========================================="
