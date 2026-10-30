"""Rules for detecting unpinned and loose dependencies."""

from __future__ import annotations

import re
from typing import List

from cargo_doctor.models import Issue, Project, Severity
from cargo_doctor.rules.base import BaseRule


class WildcardDependencyRule(BaseRule):
    """Flags wildcard version dependencies (e.g. * or 1.*)."""

    id = "CARGO-PIN-001"
    name = "wildcard-dependency"
    description = "Flags dependencies using wildcard '*' versions which break build reproducibility."
    default_severity = Severity.ERROR
    fixable = True

    def check(self, project: Project) -> List[Issue]:
        issues: List[Issue] = []

        # Check all packages
        for pkg in project.all_packages:
            for dep in pkg.dependencies:
                if dep.workspace:
                    continue
                v = (dep.version or "").strip()
                if v == "*" or v == "^*" or re.match(r"^\d+\.\*(\.\*)?$", v):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            rule_name=self.name,
                            severity=Severity.ERROR,
                            message=(
                                f"Package '{pkg.name}' specifies unpinned wildcard version '{v}' "
                                f"for dependency '{dep.name}'."
                            ),
                            file_path=pkg.manifest_path,
                            line_number=dep.line_number,
                            fixable=True,
                            suggestion=f"Pin '{dep.name}' to a specific semantic version requirement (e.g., '1.0').",
                            context={
                                "crate": dep.name,
                                "current_version": v,
                                "package": pkg.name,
                                "section": dep.section,
                            },
                        )
                    )

        # Also check workspace.dependencies in workspace root
        if project.is_workspace and project.workspace:
            for dep_name, dep in project.workspace.workspace_dependencies.items():
                v = (dep.version or "").strip()
                if v == "*" or v == "^*" or re.match(r"^\d+\.\*(\.\*)?$", v):
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            rule_name=self.name,
                            severity=Severity.ERROR,
                            message=(
                                f"Workspace dependency '{dep_name}' specifies unpinned wildcard version '{v}'."
                            ),
                            file_path=project.workspace.manifest_path,
                            line_number=dep.line_number,
                            fixable=True,
                            suggestion=f"Pin '{dep_name}' to a specific semantic version in [workspace.dependencies].",
                            context={
                                "crate": dep_name,
                                "current_version": v,
                                "package": "<workspace>",
                                "section": "workspace.dependencies",
                            },
                        )
                    )

        return issues


class UnpinnedGitDependencyRule(BaseRule):
    """Flags git dependencies without an immutable commit SHA (rev) or tag."""

    id = "CARGO-PIN-002"
    name = "unpinned-git-dependency"
    description = (
        "Flags git dependencies that track mutable branches or default HEAD without a tag or rev."
    )
    default_severity = Severity.WARNING
    fixable = False

    def check(self, project: Project) -> List[Issue]:
        issues: List[Issue] = []

        for pkg in project.all_packages:
            for dep in pkg.dependencies:
                if dep.git and not dep.rev and not dep.tag:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            rule_name=self.name,
                            severity=Severity.WARNING,
                            message=(
                                f"Git dependency '{dep.name}' in package '{pkg.name}' has no immutable "
                                f"rev or tag pinned ({dep.git})."
                            ),
                            file_path=pkg.manifest_path,
                            line_number=dep.line_number,
                            fixable=False,
                            suggestion=f"Pin '{dep.name}' with 'tag = \"...\"' or 'rev = \"<commit-sha>\"'.",
                            context={
                                "crate": dep.name,
                                "git": dep.git,
                                "branch": dep.branch,
                                "package": pkg.name,
                            },
                        )
                    )

        if project.is_workspace and project.workspace:
            for dep_name, dep in project.workspace.workspace_dependencies.items():
                if dep.git and not dep.rev and not dep.tag:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            rule_name=self.name,
                            severity=Severity.WARNING,
                            message=(
                                f"Workspace git dependency '{dep_name}' has no immutable "
                                f"rev or tag pinned ({dep.git})."
                            ),
                            file_path=project.workspace.manifest_path,
                            line_number=dep.line_number,
                            fixable=False,
                            suggestion=f"Pin '{dep_name}' with 'tag = \"...\"' or 'rev = \"<commit-sha>\"'.",
                            context={
                                "crate": dep_name,
                                "git": dep.git,
                                "branch": dep.branch,
                                "package": "<workspace>",
                            },
                        )
                    )

        return issues


class OpenEndedRangeRule(BaseRule):
    """Flags open-ended inequality version bounds (e.g. >= 1.0 without upper bound)."""

    id = "CARGO-PIN-003"
    name = "open-ended-range"
    description = "Flags dependencies using open-ended version bounds (e.g. '>= 1.0') without upper limit."
    default_severity = Severity.WARNING
    fixable = False

    def check(self, project: Project) -> List[Issue]:
        issues: List[Issue] = []

        for pkg in project.all_packages:
            for dep in pkg.dependencies:
                if dep.workspace:
                    continue
                v = (dep.version or "").strip()
                if (v.startswith(">=") or v.startswith(">")) and "<" not in v and "," not in v:
                    issues.append(
                        Issue(
                            rule_id=self.id,
                            rule_name=self.name,
                            severity=Severity.WARNING,
                            message=(
                                f"Dependency '{dep.name}' in package '{pkg.name}' uses open-ended "
                                f"version requirement '{v}' without an upper bound."
                            ),
                            file_path=pkg.manifest_path,
                            line_number=dep.line_number,
                            fixable=False,
                            suggestion=f"Use standard caret version or specify upper bound, e.g. '{v}, < 2.0'.",
                            context={
                                "crate": dep.name,
                                "version": v,
                                "package": pkg.name,
                            },
                        )
                    )

        return issues
