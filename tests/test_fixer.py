"""Tests for automated autofixer engine."""

from __future__ import annotations

from pathlib import Path
from cargo_doctor.fixer import ManifestFixer, apply_fixes
from cargo_doctor.parser import parse_project
from cargo_doctor.scanner import CargoDoctor


def test_fix_edition_text():
    fixer = ManifestFixer(target_edition="2021")
    raw = """
[package]
name = "legacy"
version = "0.1.0"
edition = "2018" # Old edition comment

[dependencies]
"""
    updated, changed = fixer.fix_edition_in_text(raw)
    assert changed
    assert 'edition = "2021" # Old edition comment' in updated


def test_fix_missing_edition_text():
    fixer = ManifestFixer(target_edition="2021")
    raw = """
[package]
name = "no-edition"
version = "0.1.0"

[dependencies]
"""
    updated, changed = fixer.fix_missing_edition_text(raw) if hasattr(fixer, "fix_missing_edition_text") else fixer.fix_edition_in_text(raw)
    assert changed
    assert 'edition = "2021"' in updated


def test_fix_metadata_text():
    fixer = ManifestFixer()
    raw = """
[package]
name = "bare"
version = "0.1.0"
edition = "2021"
"""
    missing = {"description", "license", "readme", "rust-version"}
    updated, changed = fixer.fix_metadata_in_text(raw, "bare", missing)
    assert changed
    assert 'description = "bare implementation"' in updated
    assert 'license = "MIT OR Apache-2.0"' in updated
    assert 'readme = "README.md"' in updated
    assert 'rust-version = "1.70.0"' in updated


def test_fix_wildcard_text():
    fixer = ManifestFixer()
    raw = """
[dependencies]
tokio = "*" # Wildcard
serde = { version = "*", features = ["derive"] }
"""
    updated, ch1 = fixer.fix_wildcard_in_text(raw, "tokio", "1.35.0")
    assert ch1
    assert 'tokio = "1.35.0" # Wildcard' in updated

    updated2, ch2 = fixer.fix_wildcard_in_text(updated, "serde", "1.0.195")
    assert ch2
    assert 'serde = { version = "1.0.195", features = ["derive"] }' in updated2


def test_fix_dependency_version_text():
    fixer = ManifestFixer()
    raw = """
[dependencies]
tokio = "1.28.0"
"""
    updated, changed = fixer.fix_dependency_version_in_text(raw, "tokio", "1.35.0")
    assert changed
    assert 'tokio = "1.35.0"' in updated


def test_fix_workspace_inheritance_text():
    fixer = ManifestFixer()
    raw = """
[dependencies]
serde = "1.0.190"
tokio = { version = "1.20.0", features = ["sync"] }
"""
    up1, ch1 = fixer.fix_workspace_inheritance_in_text(raw, "serde")
    assert ch1
    assert "serde = { workspace = true }" in up1

    up2, ch2 = fixer.fix_workspace_inheritance_in_text(up1, "tokio")
    assert ch2
    assert "tokio = { workspace = true, features = [\"sync\"] }" in up2


def test_apply_fixes_dry_run(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "my-crate"
version = "0.1.0"
edition = "2018"
"""
    })

    doctor = CargoDoctor()
    result = doctor.fix(proj_dir, dry_run=True, fix_edition=True)

    assert result.dry_run
    assert len(result.files_modified) == 1
    assert result.fixed_issues_count >= 1
    assert proj_dir / "Cargo.toml" in result.diffs

    # Ensure file on disk was NOT modified in dry-run
    content = (proj_dir / "Cargo.toml").read_text(encoding="utf-8")
    assert 'edition = "2018"' in content


def test_apply_fixes_with_backup(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "my-crate"
version = "0.1.0"
edition = "2018"
"""
    })

    doctor = CargoDoctor()
    result = doctor.fix(proj_dir, dry_run=False, backup=True, fix_edition=True)

    assert not result.dry_run
    assert len(result.files_modified) == 1

    # File on disk should now have edition 2021
    manifest = proj_dir / "Cargo.toml"
    assert 'edition = "2021"' in manifest.read_text(encoding="utf-8")

    # Backup file should exist and have edition 2018
    backup_file = proj_dir / "Cargo.toml.bak"
    assert backup_file.is_file()
    assert 'edition = "2018"' in backup_file.read_text(encoding="utf-8")
