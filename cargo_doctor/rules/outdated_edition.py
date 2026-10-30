"""Rules for detecting outdated or missing Rust edition declarations."""

from __future__ import annotations

from typing import List

from cargo_doctor.models import Issue, Project, Severity
from cargo_doctor.rules.base import BaseRule

MODERN_EDITIONS = {"2021", "2024"}
LEGACY_EDITIONS = {"2015", "2018"}


class OutdatedEditionRule(BaseRule):
    """Flags packages using legacy Rust editions (2015, 2018)."""

    id = "CARGO-EDT-001"
    name = "outdated-edition"
    description = (
        "Detects packages using legacy Rust editions (2015, 2018) and recommends upgrading to 2021 or 2024."
    )
    default_severity = Severity.WARNING
    fixable = True

    def check(self, project: Project) -> List[Issue]:
        issues: List[Issue] = []

        for pkg in project.all_packages:
            if pkg.edition in LEGACY_EDITIONS:
                # Find line number if possible
                content = pkg.manifest_path.read_text(encoding="utf-8")
                lines = content.splitlines()
                line_no = None
                for idx, line in enumerate(lines, 1):
                    if line.strip().startswith("edition") and "=" in line:
                        line_no = idx
                        break

                issues.append(
                    Issue(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=Severity.WARNING,
                        message=(
                            f"Package '{pkg.name}' specifies outdated Rust edition '{pkg.edition}'."
                        ),
                        file_path=pkg.manifest_path,
                        line_number=line_no,
                        fixable=True,
                        suggestion="Upgrade to 'edition = \"2021\"' or 'edition = \"2024\"'.",
                        context={
                            "package": pkg.name,
                            "current_edition": pkg.edition,
                            "target_edition": "2021",
                        },
                    )
                )

        return issues


class MissingEditionRule(BaseRule):
    """Flags packages with no edition declared (defaults to 2015 in Cargo)."""

    id = "CARGO-EDT-002"
    name = "missing-edition"
    description = (
        "Flags packages missing an explicit edition key (Cargo defaults to legacy 2015 edition)."
    )
    default_severity = Severity.WARNING
    fixable = True

    def check(self, project: Project) -> List[Issue]:
        issues: List[Issue] = []

        for pkg in project.all_packages:
            if not pkg.edition:
                # Find line of [package]
                content = pkg.manifest_path.read_text(encoding="utf-8")
                lines = content.splitlines()
                line_no = None
                for idx, line in enumerate(lines, 1):
                    if line.strip() == "[package]":
                        line_no = idx
                        break

                issues.append(
                    Issue(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=Severity.WARNING,
                        message=(
                            f"Package '{pkg.name}' does not declare an edition (defaults to legacy 2015)."
                        ),
                        file_path=pkg.manifest_path,
                        line_number=line_no,
                        fixable=True,
                        suggestion="Add 'edition = \"2021\"' under [package].",
                        context={
                            "package": pkg.name,
                            "current_edition": None,
                            "target_edition": "2021",
                        },
                    )
                )

        return issues
