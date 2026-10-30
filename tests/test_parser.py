"""Tests for Cargo manifest and workspace parser."""

from __future__ import annotations

from pathlib import Path
from cargo_doctor.parser import (
    find_line_number,
    load_toml,
    parse_package,
    parse_project,
)


def test_find_line_number():
    content = """
[package]
name = "my-crate"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = "1.0"
tokio = { version = "1.0", features = ["full"] }
"""
    lines = content.splitlines()
    assert find_line_number(lines, section="package", key="name") == 3
    assert find_line_number(lines, section="package", key="edition") == 5
    assert find_line_number(lines, section="dependencies", key="serde") == 8
    assert find_line_number(lines, section="dependencies", key="tokio") == 9


def test_parse_single_package(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "single-crate"
version = "1.2.3"
edition = "2021"
description = "A test crate"
license = "MIT"
repository = "https://github.com/example/single-crate"
readme = "README.md"
rust-version = "1.75.0"
keywords = ["test", "cargo"]
categories = ["development-tools"]
authors = ["Alice <alice@example.com>"]

[dependencies]
serde = "1.0.190"
tokio = { version = "1.30", features = ["sync"], optional = true }

[dev-dependencies]
pytest-mock = "0.1"

[build-dependencies]
cc = "1.0"

[target.'cfg(windows)'.dependencies]
winapi = "0.3"
"""
    })

    proj = parse_project(proj_dir)
    assert not proj.is_workspace
    assert len(proj.packages) == 1
    pkg = proj.packages[0]
    assert pkg.name == "single-crate"
    assert pkg.version == "1.2.3"
    assert pkg.edition == "2021"
    assert pkg.description == "A test crate"
    assert pkg.license == "MIT"
    assert pkg.repository == "https://github.com/example/single-crate"
    assert pkg.readme == "README.md"
    assert pkg.rust_version == "1.75.0"
    assert pkg.keywords == ["test", "cargo"]
    assert pkg.categories == ["development-tools"]
    assert pkg.authors == ["Alice <alice@example.com>"]

    # Dependencies check
    dep_names = {d.name: d for d in pkg.dependencies}
    assert "serde" in dep_names
    assert dep_names["serde"].version == "1.0.190"
    assert dep_names["serde"].section == "dependencies"

    assert "tokio" in dep_names
    assert dep_names["tokio"].optional is True
    assert dep_names["tokio"].features == ["sync"]

    assert "pytest-mock" in dep_names
    assert dep_names["pytest-mock"].section == "dev-dependencies"

    assert "cc" in dep_names
    assert dep_names["cc"].section == "build-dependencies"

    assert "winapi" in dep_names
    assert dep_names["winapi"].target in ("cfg(windows)", "'cfg(windows)'")


def test_parse_virtual_workspace(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[workspace]
members = [
    "crates/*",
    "tools/cli",
]
exclude = [
    "crates/ignored",
]

[workspace.dependencies]
tokio = { version = "1.35.0", features = ["rt-multi-thread"] }
serde = "1.0.195"
""",
        "crates/core/Cargo.toml": """
[package]
name = "core-crate"
version = "0.1.0"
edition = "2021"

[dependencies]
tokio = { workspace = true }
""",
        "crates/ignored/Cargo.toml": """
[package]
name = "ignored-crate"
version = "0.1.0"
edition = "2018"
""",
        "tools/cli/Cargo.toml": """
[package]
name = "cli-crate"
version = "0.2.0"
edition = "2021"

[dependencies]
serde = { workspace = true }
"""
    })

    proj = parse_project(proj_dir)
    assert proj.is_workspace
    assert proj.workspace is not None
    assert proj.workspace.is_virtual

    # Excluded member should not be included
    member_names = [m.name for m in proj.workspace.members]
    assert "core-crate" in member_names
    assert "cli-crate" in member_names
    assert "ignored-crate" not in member_names

    # Workspace dependencies check
    ws_deps = proj.workspace.workspace_dependencies
    assert "tokio" in ws_deps
    assert ws_deps["tokio"].version == "1.35.0"
    assert "serde" in ws_deps
    assert ws_deps["serde"].version == "1.0.195"

    # Member dependency inheritance
    core_pkg = next(m for m in proj.workspace.members if m.name == "core-crate")
    core_tokio = core_pkg.dependencies[0]
    assert core_tokio.name == "tokio"
    assert core_tokio.is_workspace_inherited
