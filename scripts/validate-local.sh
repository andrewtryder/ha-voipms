#!/usr/bin/env bash
set -euo pipefail

# Portfolio Universal Local Validation Contract
# Repository: ha-voipms
# Gate: 90% component statement coverage (offline/mock-only SMS safety isolation)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -n $(git ls-files --others --exclude-standard) ]]; then
    echo "Error: move or commit untracked files before validation" >&2
    exit 1
fi

# Compare both index and working-tree changes, including untracked paths.
snapshot_dir=$(mktemp -d)
snapshot() {
    git status --porcelain=v1 --untracked-files=all > "$1/status"
    git diff --binary > "$1/worktree"
    git diff --cached --binary > "$1/index"
}
mkdir "$snapshot_dir/before" "$snapshot_dir/after"
snapshot "$snapshot_dir/before"
check_changes() {
    snapshot "$snapshot_dir/after"
    if ! diff -qr "$snapshot_dir/before" "$snapshot_dir/after" >/dev/null; then
        echo "Error: validation changed the working tree or index:" >&2
        git status --short >&2
        return 1
    fi
}
finish() {
    local result=$?
    check_changes || result=1
    rm -rf "$snapshot_dir"
    return "$result"
}
trap finish EXIT

echo "==> [1/6] Verifying toolchain and interpreter"
command -v python3.14 >/dev/null 2>&1 || { echo "Error: Python 3.14.2 or newer is required" >&2; exit 1; }
command -v uv >/dev/null 2>&1 || { echo "Error: uv is required" >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "Error: npm is required" >&2; exit 1; }
python3.14 -c 'import sys; assert sys.version_info >= (3, 14, 2), "Python 3.14.2 or newer is required"; print(sys.version)'
python3.14 -m venv "$snapshot_dir/venv"
uv pip sync --python "$snapshot_dir/venv/bin/python" requirements-dev.lock
export PATH="$snapshot_dir/venv/bin:$PATH"

echo "==> [2/6] Running pre-commit hooks on all files"
pre-commit run --all-files

echo "==> [3/6] Running Ruff lint and formatting checks"
ruff check .
ruff format --check .

echo "==> [4/6] Building frontend Lovelace card"
(cd frontend && npm ci && npx --no-install tsc --noEmit && npm run build)

echo "==> [5/6] Running Python test suite with offline mock isolation (>=90% coverage)"
coverage run -m pytest --disable-socket --allow-unix-socket tests/
coverage report --fail-under=90

echo "==> [6/6] Checking for changes made by validation"
check_changes

echo "==> Local validation passed successfully!"
