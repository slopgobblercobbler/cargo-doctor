"""Rules for recommending workspace dependency centralization."""

from __future__ import annotations

from typing import Dict, List, Tuple

from cargo_doctor.models import Dependency, Issue, Package, Project, Severity
from cargo_doctor.rules.base import BaseRule


class WorkspaceInheritanceRecommendationRule(BaseRule):
    """Recommends hoisting common dependencies used across multiple members to [workspace.dependencies]."""

    id = "CARGO-WS-001"
    name = "recommend-workspace-dependencies"
    description = (
        "Recommends centralizing dependencies shared across 2 or more workspace members "
        "into [workspace.dependencies]."
    )
    default_severity = Severity.SUGGESTION
    fixable = False

    def check(self, project: Project) -> List[Issue]:
        issues: List[Issue] = []
        if not project.is_workspace or not project.workspace:
            return issues

        ws_deps = project.workspace.workspace_dependencies

        # Group dependencies across members
        dep_occurrences: Dict[str, List[Tuple[Package, Dependency]]] = {}
        for pkg in project.workspace.members:
            for dep in pkg.dependencies:
                if dep.workspace:
                    continue  # already workspace inherited
                if dep.path and not dep.version:
                    continue  # local path member
                dep_occurrences.setdefault(dep.name, []).append((pkg, dep))

        for dep_name, occurrences in dep_occurrences.items():
            if dep_name in ws_deps:
                continue  # Handled by CARGO-DUP-002

            # If 2 or more members use this dependency
            distinct_pkgs = {pkg.name for pkg, _ in occurrences}
            if len(distinct_pkgs) >= 2:
                pkgs_list = ", ".join(sorted(distinct_pkgs))
                issues.append(
                    Issue(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=Severity.SUGGESTION,
                        message=(
                            f"Dependency '{dep_name}' is used across {len(distinct_pkgs)} members "
                            f"({pkgs_list}) but is not centralized in [workspace.dependencies]."
                        ),
                        file_path=project.workspace.manifest_path,
                        fixable=False,
                        suggestion=(
                            f"Add '{dep_name}' to [workspace.dependencies] and use "
                            f"'{dep_name}.workspace = true' in member crates."
                        ),
                        context={
                            "crate": dep_name,
                            "members": list(distinct_pkgs),
                        },
                    )
                )

        return issues
