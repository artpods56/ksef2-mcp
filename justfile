sync:
    uv sync

test:
    uv run pytest

lint:
    uv run ruff check src tests

format:
    uv run ruff format src tests

format-check:
    uv run ruff format --check src tests

typecheck:
    uv run basedpyright src tests

check:
    just lint
    just format-check
    just typecheck
    just test
