"""Test fixtures and temporary workspace generators."""

from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture
def temp_project(tmp_path: Path):
    """Factory fixture for creating temporary Cargo projects."""
    def _create_project(files: dict[str, str]) -> Path:
        for rel_path, content in files.items():
            file_path = tmp_path / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content.strip(), encoding="utf-8")
        return tmp_path

    return _create_project
