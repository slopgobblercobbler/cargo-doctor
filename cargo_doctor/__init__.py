"""cargo-doctor: Lint, detect duplicates, and autofix Rust Cargo manifests and workspaces."""

from __future__ import annotations

from cargo_doctor.models import (
    Dependency,
    FixResult,
    Issue,
    Package,
    Project,
    ScanResult,
    Severity,
    Workspace,
)
from cargo_doctor.parser import parse_project
from cargo_doctor.scanner import CargoDoctor

__version__ = "0.1.0"
__all__ = [
    "CargoDoctor",
    "Dependency",
    "FixResult",
    "Issue",
    "Package",
    "Project",
    "ScanResult",
    "Severity",
    "Workspace",
    "parse_project",
    "inspect_project",
    "fix_project",
    "scan_project",
]


def inspect_project(path=".", **kwargs):
    """Convenience helper to inspect a Cargo project."""
    return CargoDoctor(**kwargs).inspect(path)


def fix_project(path=".", **kwargs):
    """Convenience helper to fix a Cargo project."""
    return CargoDoctor().fix(path, **kwargs)


def scan_project(path=".", **kwargs):
    """Convenience helper to scan a Cargo project."""
    return CargoDoctor(**kwargs).scan(path)
