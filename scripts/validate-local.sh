#!/usr/bin/env bash
set -euo pipefail

# Portfolio Universal Local Validation Contract
# Repository: ha-voipms
# Gate: 90% component statement coverage (offline/mock-only SMS safety isolation)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -d "$REPO_ROOT/.venv/bin" ]]; then
    export PATH="$REPO_ROOT/.venv/bin:$PATH"
fi

echo "==> [1/6] Verifying toolchain and interpreter"
python --version

echo "==> [2/6] Running pre-commit hooks on all files"
pre-commit run --all-files

echo "==> [3/6] Running Ruff lint and formatting checks"
ruff check .
ruff format --check .

echo "==> [4/6] Building frontend Lovelace card"
if [[ -d "frontend" && -f "frontend/package.json" ]]; then
    (cd frontend && npx tsc --noEmit && npm run build)
fi

echo "==> [5/6] Running Python test suite with offline mock isolation (>=90% coverage)"
coverage run -m pytest tests/
coverage report --fail-under=90

echo "==> [6/6] Verifying clean git working tree"
git diff --exit-code

echo "==> Local validation passed successfully!"
