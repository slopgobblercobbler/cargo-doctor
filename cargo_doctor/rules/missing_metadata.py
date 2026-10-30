"""Rules for checking missing package metadata."""

from __future__ import annotations

from typing import List

from cargo_doctor.models import Issue, Project, Severity
from cargo_doctor.rules.base import BaseRule


class MissingDescriptionRule(BaseRule):
    """Flags packages missing a description."""

    id = "CARGO-META-001"
    name = "missing-description"
    description = "Checks that packages declare a description."
    default_severity = Severity.WARNING
    fixable = True

    def check(self, project: Project) -> List[Issue]:
        issues: List[Issue] = []
        for pkg in project.all_packages:
            if not pkg.description or not pkg.description.strip():
                severity = Severity.WARNING if pkg.is_publishable else Severity.INFO
                issues.append(
                    Issue(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=severity,
                        message=f"Package '{pkg.name}' is missing a 'description' in [package].",
                        file_path=pkg.manifest_path,
                        fixable=True,
                        suggestion=f'Add description = "{pkg.name} library" to [package].',
                        context={"package": pkg.name, "field": "description"},
                    )
                )
        return issues


class MissingLicenseRule(BaseRule):
    """Flags packages missing license or license-file."""

    id = "CARGO-META-002"
    name = "missing-license"
    description = "Checks that packages specify a license or license-file."
    default_severity = Severity.WARNING
    fixable = True

    def check(self, project: Project) -> List[Issue]:
        issues: List[Issue] = []
        for pkg in project.all_packages:
            if not pkg.license and not pkg.license_file:
                severity = Severity.WARNING if pkg.is_publishable else Severity.INFO
                issues.append(
                    Issue(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=severity,
                        message=f"Package '{pkg.name}' has no 'license' or 'license-file' declared.",
                        file_path=pkg.manifest_path,
                        fixable=True,
                        suggestion='Add license = "MIT OR Apache-2.0" to [package].',
                        context={"package": pkg.name, "field": "license"},
                    )
                )
        return issues


class MissingRepositoryRule(BaseRule):
    """Flags packages missing repository URL."""

    id = "CARGO-META-003"
    name = "missing-repository"
    description = "Checks that packages specify a source repository URL."
    default_severity = Severity.SUGGESTION
    fixable = False

    def check(self, project: Project) -> List[Issue]:
        issues: List[Issue] = []
        for pkg in project.all_packages:
            if not pkg.repository:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=Severity.SUGGESTION,
                        message=f"Package '{pkg.name}' is missing a 'repository' URL.",
                        file_path=pkg.manifest_path,
                        fixable=False,
                        suggestion='Add repository = "https://github.com/..." to [package].',
                        context={"package": pkg.name, "field": "repository"},
                    )
                )
        return issues


class MissingReadmeRule(BaseRule):
    """Flags packages missing readme definition."""

    id = "CARGO-META-004"
    name = "missing-readme"
    description = "Checks that packages declare a readme file."
    default_severity = Severity.SUGGESTION
    fixable = True

    def check(self, project: Project) -> List[Issue]:
        issues: List[Issue] = []
        for pkg in project.all_packages:
            if not pkg.readme:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=Severity.SUGGESTION,
                        message=f"Package '{pkg.name}' has no 'readme' specified.",
                        file_path=pkg.manifest_path,
                        fixable=True,
                        suggestion='Add readme = "README.md" to [package].',
                        context={"package": pkg.name, "field": "readme"},
                    )
                )
        return issues


class MissingMSRVRule(BaseRule):
    """Flags packages missing Minimum Supported Rust Version (rust-version)."""

    id = "CARGO-MSRV-001"
    name = "missing-rust-version"
    description = "Checks that packages specify rust-version (MSRV) for consumer compatibility."
    default_severity = Severity.SUGGESTION
    fixable = True

    def check(self, project: Project) -> List[Issue]:
        issues: List[Issue] = []
        for pkg in project.all_packages:
            if not pkg.rust_version:
                issues.append(
                    Issue(
                        rule_id=self.id,
                        rule_name=self.name,
                        severity=Severity.SUGGESTION,
                        message=f"Package '{pkg.name}' does not declare 'rust-version' (MSRV).",
                        file_path=pkg.manifest_path,
                        fixable=True,
                        suggestion='Add rust-version = "1.70.0" to [package].',
                        context={"package": pkg.name, "field": "rust-version"},
                    )
                )
        return issues
