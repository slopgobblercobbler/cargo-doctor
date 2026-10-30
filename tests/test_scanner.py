"""Tests for project scanner and health score calculations."""

from __future__ import annotations

from cargo_doctor import CargoDoctor, fix_project, inspect_project, scan_project
from cargo_doctor.models import Severity


def test_scan_healthy_project(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "healthy-crate"
version = "0.1.0"
edition = "2021"
description = "A perfectly healthy crate"
license = "MIT"
repository = "https://github.com/example/healthy-crate"
readme = "README.md"
rust-version = "1.75.0"

[dependencies]
serde = "1.0.195"
"""
    })

    doctor = CargoDoctor()
    result = doctor.scan(proj_dir)

    assert result.health_score == 100
    assert result.grade == "A"
    assert result.errors_count == 0
    assert result.warnings_count == 0
    assert result.packages_count == 1
    assert result.unique_dependencies_count == 1
    assert result.editions == {"2021": 1}

    # Serialization test
    d = result.to_dict()
    assert d["health_score"] == 100
    assert d["grade"] == "A"


def test_scan_flawed_project(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[workspace]
members = ["crates/*"]
""",
        "crates/a/Cargo.toml": """
[package]
name = "a"
version = "0.1.0"
edition = "2018"

[dependencies]
foo = "*"
syn = "1.0"
""",
        "crates/b/Cargo.toml": """
[package]
name = "b"
version = "0.1.0"

[dependencies]
syn = "2.0"
"""
    })

    doctor = CargoDoctor()
    result = doctor.scan(proj_dir)

    # Flawed project has errors and warnings
    assert result.errors_count > 0
    assert result.health_score < 80
    assert result.grade in ("C", "D", "F")
    assert result.packages_count == 2
    assert "2018" in result.editions


def test_convenience_functions(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "mini-crate"
version = "0.1.0"
edition = "2021"
"""
    })

    issues = inspect_project(proj_dir)
    assert isinstance(issues, list)

    scan_res = scan_project(proj_dir)
    assert scan_res.packages_count == 1

    fix_res = fix_project(proj_dir, dry_run=True)
    assert fix_res.dry_run
