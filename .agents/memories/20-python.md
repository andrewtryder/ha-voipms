# Python Rules

Use the existing dependency workflow unless the task explicitly migrates package management.

Preferred checks:

- `./scripts/validate-local.sh`
- `ruff format --check .`
- `ruff check .`
- `pytest`
- `coverage run -m pytest && coverage report`

Use Ruff for formatting/linting and pytest for tests when configured.

## Related docs

- `README.md`
- `CONTRIBUTING.md`
- `AGENTS.md`
