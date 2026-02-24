# AGENTS.md

## Project intent
Pawlabeling is being modernized as a Python 3 desktop application with a clean core, SQLite storage, and a Qt + pygfx visualization layer.
Do not attempt to revive the legacy conda environment, Python 2 stack, or legacy CI.

## Baseline
- Python: 3.12
- Tooling: uv, ruff, pytest
- Packaging: pyproject.toml only; no setup.py driven workflows
- Layout: src/ package layout

## Setup commands
- Install and sync dev deps: `uv sync --group dev`
- Run lint: `uv run ruff check .`
- Run tests: `uv run pytest`

## Quality gates
Before every commit:
- `uv run ruff check .`
- `uv run pytest`

Prefer small commits with focused messages.

## Architecture direction
- Storage: SQLite as embedded database
  - Prefer SQLAlchemy 2.0 (or SQLModel) with an explicit repository layer
  - Add migrations early (Alembic) once schema stabilizes
- UI: Qt
  - Prefer PySide6 unless a dependency requires PyQt
- Visualization: pygfx for interactive rendering
  - Use Qt integration via rendercanvas and embed in the main window
  - If higher level plotting is needed, fastplotlib is acceptable

## Migration stance
- Legacy code may be referenced for behavior and file format understanding only.
- Port minimal, validated logic into new modules with tests; do not carry over old architecture.

## Conventions
- Type hints for new code.
- Tests for new modules and bug fixes.
- Keep public APIs small; prefer internal modules with clear boundaries.
