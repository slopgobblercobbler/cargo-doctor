"""Project scanner and high-level CargoDoctor API."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from cargo_doctor.fixer import apply_fixes
from cargo_doctor.models import FixResult, Issue, Project, ScanResult, Severity
from cargo_doctor.parser import parse_project
from cargo_doctor.rules import get_rules


class CargoDoctor:
    """High-level inspection and autofix coordinator for Cargo projects."""

    def __init__(
        self,
        target_edition: str = "2021",
        include_rules: Optional[List[str]] = None,
        exclude_rules: Optional[List[str]] = None,
    ):
        self.target_edition = target_edition
        self.include_rules = include_rules
        self.exclude_rules = exclude_rules
        self.rules = get_rules(include_rules, exclude_rules)

    def load_project(self, path: Union[str, Path]) -> Project:
        """Parse project and workspace structure."""
        return parse_project(path)

    def inspect(
        self,
        path: Union[str, Path],
        project: Optional[Project] = None,
    ) -> List[Issue]:
        """Run all registered rules against the project and return detected issues."""
        if project is None:
            project = self.load_project(path)

        all_issues: List[Issue] = []
        for rule in self.rules:
            issues = rule.check(project)
            all_issues.extend(issues)

        # Sort issues: Errors first, then Warnings, then Suggestions, then by file/line
        severity_order = {
            Severity.ERROR: 0,
            Severity.WARNING: 1,
            Severity.SUGGESTION: 2,
            Severity.INFO: 3,
        }
        all_issues.sort(
            key=lambda x: (
                severity_order.get(x.severity, 99),
                str(x.file_path),
                x.line_number or 0,
            )
        )
        return all_issues

    def scan(
        self,
        path: Union[str, Path],
        project: Optional[Project] = None,
    ) -> ScanResult:
        """Perform a comprehensive project health scan with scoring and metrics."""
        if project is None:
            project = self.load_project(path)

        issues = self.inspect(path, project=project)

        # Collect stats
        packages = project.all_packages
        editions: Dict[str, int] = {}
        all_deps: List[str] = []
        unique_deps: Set[str] = set()

        for pkg in packages:
            edt = pkg.edition or "missing (default 2015)"
            editions[edt] = editions.get(edt, 0) + 1
            for dep in pkg.dependencies:
                all_deps.append(dep.name)
                unique_deps.add(dep.name)

        # Calculate health score: 100 base, deductions for problems
        score = 100
        for issue in issues:
            if issue.severity == Severity.ERROR:
                score -= 10
            elif issue.severity == Severity.WARNING:
                score -= 4
            elif issue.severity == Severity.SUGGESTION:
                score -= 1

        score = max(0, min(100, score))

        # Assign letter grade
        if score >= 90:
            grade = "A"
        elif score >= 75:
            grade = "B"
        elif score >= 55:
            grade = "C"
        elif score >= 35:
            grade = "D"
        else:
            grade = "F"

        return ScanResult(
            project_path=project.root_path,
            is_workspace=project.is_workspace,
            packages_count=len(packages),
            total_dependencies_count=len(all_deps),
            unique_dependencies_count=len(unique_deps),
            health_score=score,
            grade=grade,
            issues=issues,
            editions=editions,
        )

    def fix(
        self,
        path: Union[str, Path],
        dry_run: bool = False,
        backup: bool = False,
        fix_edition: bool = True,
        fix_duplicates: bool = True,
        fix_unpinned: bool = True,
        fix_metadata: bool = True,
    ) -> FixResult:
        """Inspect and apply autofixes to project files."""
        project = self.load_project(path)
        issues = self.inspect(path, project=project)

        return apply_fixes(
            project=project,
            issues=issues,
            dry_run=dry_run,
            backup=backup,
            fix_edition=fix_edition,
            fix_duplicates=fix_duplicates,
            fix_unpinned=fix_unpinned,
            fix_metadata=fix_metadata,
            target_edition=self.target_edition,
        )
