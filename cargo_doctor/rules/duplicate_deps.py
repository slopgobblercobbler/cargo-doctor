"""Rules for detecting duplicate and mismatched dependencies across workspace members."""

from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

from cargo_doctor.models import Dependency, Issue, Package, Project, Severity
from cargo_doctor.rules.base import BaseRule


def parse_major_version(ver_str: str) -> Tuple[int, int, int]:
    """Parse semver string into (major, minor, patch) integers for comparison."""
    clean = re.sub(r"^[^\d]*", "", ver_str.strip())
    parts = clean.split(".")
    nums = []
    for p in parts[:3]:
        # Strip suffix like -alpha, +build
        match = re.match(r"^(\d+)", p)
        if match:
            nums.append(int(match.group(1)))
        else:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])


class DuplicateDependencyRule(BaseRule):
    """Detects conflicting or mismatched versions of the same dependency across workspace members."""

    id = "CARGO-DUP-001"
    name = "duplicate-dependency-versions"
    description = (
        "Detects different version requirements for the same crate across workspace members."
    )
    default_severity = Severity.WARNING
    fixable = True

    def check(self, project: Project) -> List[Issue]:
        issues: List[Issue] = []
        if not project.is_workspace or not project.workspace:
            return issues

        # Collect dependencies by crate name across all workspace members
        # dep_map: crate_name -> list of (package, Dependency)
        dep_map: Dict[str, List[Tuple[Package, Dependency]]] = {}

        for pkg in project.workspace.members:
            for dep in pkg.dependencies:
                # If dependency inherits from workspace, its version is managed at workspace level
                if dep.workspace:
                    continue
                # If it's a local path-only dependency without version, skip
                if dep.path and not dep.version:
                    continue
                if dep.version:
                    dep_map.setdefault(dep.name, []).append((pkg, dep))

        # Check for divergence
        for dep_name, occurrences in dep_map.items():
            versions: Dict[str, List[Tuple[Package, Dependency]]] = {}
            for pkg, dep in occurrences:
                v = (dep.version or "").strip()
                versions.setdefault(v, []).append((pkg, dep))

            if len(versions) > 1:
                # Multiple distinct versions found across workspace members!
                # Check if major version differs
                major_versions: Set[int] = set()
                highest_semver = (0, 0, 0)
                highest_ver_str = ""

                for v in versions.keys():
                    try:
                        parsed = parse_major_version(v)
                        major_versions.add(parsed[0])
                        if parsed > highest_semver:
                            highest_semver = parsed
                            highest_ver_str = v
                    except Exception:
                        pass

                severity = Severity.ERROR if len(major_versions) > 1 else Severity.WARNING

                # Format human readable summary of conflicting versions
                conflicts_summary = ", ".join(
                    f"{pkg.name}: '{v}'" for v, pkgs in versions.items() for pkg, _ in pkgs
                )

                for v, pkgs in versions.items():
                    for pkg, dep in pkgs:
                        issues.append(
                            Issue(
                                rule_id=self.id,
                                rule_name=self.name,
                                severity=severity,
                                message=(
                                    f"Conflicting versions for crate '{dep_name}' across workspace members: "
                                    f"'{pkg.name}' uses '{v}', while workspace has [{conflicts_summary}]."
                                ),
                                file_path=pkg.manifest_path,
                                line_number=dep.line_number,
                                fixable=True,
                                suggestion=(
                                    f"Standardize '{dep_name}' to '{highest_ver_str}' "
                                    f"or inherit from [workspace.dependencies]."
                                ),
                                context={
                                    "crate": dep_name,
                                    "current_version": v,
                                    "target_version": highest_ver_str,
                                    "package": pkg.name,
                                    "all_versions": list(versions.keys()),
                                },
                            )
                        )

        return issues


class WorkspaceInheritanceMismatchRule(BaseRule):
    """Detects when a dependency is in workspace.dependencies but member defines it directly."""

    id = "CARGO-DUP-002"
    name = "uninherited-workspace-dependency"
    description = (
        "Identifies dependencies defined in [workspace.dependencies] that are duplicated inline "
        "in members instead of using workspace = true."
    )
    default_severity = Severity.WARNING
    fixable = True

    def check(self, project: Project) -> List[Issue]:
        issues: List[Issue] = []
        if not project.is_workspace or not project.workspace:
            return issues

        ws_deps = project.workspace.workspace_dependencies
        if not ws_deps:
            return issues

        for pkg in project.workspace.members:
            # Skip root package if virtual workspace manifest is checked
            if (
                not project.workspace.is_virtual
                and pkg.manifest_path == project.workspace.manifest_path
            ):
                continue

            for dep in pkg.dependencies:
                if dep.name in ws_deps and not dep.workspace:
                    ws_spec = ws_deps[dep.name]
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            rule_name=self.name,
                            severity=Severity.WARNING,
                            message=(
                                f"Dependency '{dep.name}' in package '{pkg.name}' is explicitly specified "
                                f"with version '{dep.version or dep.spec}', but is already configured in "
                                f"[workspace.dependencies]."
                            ),
                            file_path=pkg.manifest_path,
                            line_number=dep.line_number,
                            fixable=True,
                            suggestion=f"Replace inline definition with '{dep.name}.workspace = true'.",
                            context={
                                "crate": dep.name,
                                "package": pkg.name,
                                "section": dep.section,
                                "ws_version": ws_spec.version,
                            },
                        )
                    )

        return issues
