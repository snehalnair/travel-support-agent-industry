from tsa import main


def test_package_imports_and_exposes_entrypoint() -> None:
    """Proves the src-layout package installs and imports correctly."""
    assert callable(main)

# 1. Format the codebase
uv run ruff format

# 2. Fix lint errors automatically
uv run ruff check --fix

# 3. Regenerate and lock your dependencies
uv lock

# 4. Verify your entrypoint test passes locally
uv run pytest