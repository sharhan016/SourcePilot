from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_repository_metadata_uses_canonical_name() -> None:
    assert 'name = "sourcepilot"' in (ROOT / "pyproject.toml").read_text()
    assert "# SourcePilot" in (ROOT / "README.md").read_text()
    assert "name: sourcepilot" in (ROOT / "compose.yaml").read_text()


def test_compose_contains_required_services() -> None:
    compose = (ROOT / "compose.yaml").read_text()
    for service in ("postgres:", "api:", "worker:", "web:"):
        assert service in compose
