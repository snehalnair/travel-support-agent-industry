from tsa import main


def test_package_imports_and_exposes_entrypoint() -> None:
    """Proves the src-layout package installs and imports correctly."""
    assert callable(main)

uv run ruff format .