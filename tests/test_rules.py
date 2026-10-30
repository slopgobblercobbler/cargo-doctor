"""Tests for inspection rules."""

from __future__ import annotations

from cargo_doctor.models import Severity
from cargo_doctor.parser import parse_project
from cargo_doctor.rules import get_rules
from cargo_doctor.rules.duplicate_deps import (
    DuplicateDependencyRule,
    WorkspaceInheritanceMismatchRule,
    parse_major_version,
)
from cargo_doctor.rules.missing_metadata import (
    MissingDescriptionRule,
    MissingLicenseRule,
    MissingMSRVRule,
    MissingReadmeRule,
    MissingRepositoryRule,
)
from cargo_doctor.rules.outdated_edition import (
    MissingEditionRule,
    OutdatedEditionRule,
)
from cargo_doctor.rules.unpinned_crates import (
    OpenEndedRangeRule,
    UnpinnedGitDependencyRule,
    WildcardDependencyRule,
)
from cargo_doctor.rules.workspace_inheritance import (
    WorkspaceInheritanceRecommendationRule,
)


def test_parse_major_version():
    assert parse_major_version("1.2.3") == (1, 2, 3)
    assert parse_major_version("^2.0") == (2, 0, 0)
    assert parse_major_version("0.1.0-alpha.1") == (0, 1, 0)
    assert parse_major_version("10") == (10, 0, 0)


def test_duplicate_dependency_rule_conflict(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[workspace]
members = ["crates/*"]
""",
        "crates/a/Cargo.toml": """
[package]
name = "crate-a"
version = "0.1.0"
edition = "2021"

[dependencies]
tokio = "1.28.0"
""",
        "crates/b/Cargo.toml": """
[package]
name = "crate-b"
version = "0.1.0"
edition = "2021"

[dependencies]
tokio = "1.35.0"
"""
    })

    proj = parse_project(proj_dir)
    rule = DuplicateDependencyRule()
    issues = rule.check(proj)

    assert len(issues) == 2
    assert all(i.rule_id == "CARGO-DUP-001" for i in issues)
    assert all(i.severity == Severity.WARNING for i in issues)
    assert any("crate-a" in i.message for i in issues)
    assert any("crate-b" in i.message for i in issues)


def test_duplicate_dependency_rule_major_mismatch(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[workspace]
members = ["crates/*"]
""",
        "crates/a/Cargo.toml": """
[package]
name = "crate-a"
version = "0.1.0"
edition = "2021"

[dependencies]
syn = "1.0.100"
""",
        "crates/b/Cargo.toml": """
[package]
name = "crate-b"
version = "0.1.0"
edition = "2021"

[dependencies]
syn = "2.0.48"
"""
    })

    proj = parse_project(proj_dir)
    rule = DuplicateDependencyRule()
    issues = rule.check(proj)

    assert len(issues) == 2
    # Major mismatch should be an ERROR
    assert all(i.severity == Severity.ERROR for i in issues)


def test_workspace_inheritance_mismatch_rule(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[workspace]
members = ["crates/*"]

[workspace.dependencies]
serde = "1.0.195"
""",
        "crates/a/Cargo.toml": """
[package]
name = "crate-a"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = "1.0.190"
"""
    })

    proj = parse_project(proj_dir)
    rule = WorkspaceInheritanceMismatchRule()
    issues = rule.check(proj)

    assert len(issues) == 1
    assert issues[0].rule_id == "CARGO-DUP-002"
    assert "already configured in [workspace.dependencies]" in issues[0].message


def test_wildcard_dependency_rule(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "crate-wildcard"
version = "0.1.0"
edition = "2021"

[dependencies]
log = "*"
rand = { version = "^*" }
"""
    })

    proj = parse_project(proj_dir)
    rule = WildcardDependencyRule()
    issues = rule.check(proj)

    assert len(issues) == 2
    assert all(i.rule_id == "CARGO-PIN-001" for i in issues)
    assert all(i.severity == Severity.ERROR for i in issues)


def test_unpinned_git_dependency_rule(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "crate-git"
version = "0.1.0"
edition = "2021"

[dependencies]
my_repo = { git = "https://github.com/foo/bar", branch = "main" }
pinned_repo = { git = "https://github.com/foo/baz", rev = "abcdef123" }
"""
    })

    proj = parse_project(proj_dir)
    rule = UnpinnedGitDependencyRule()
    issues = rule.check(proj)

    assert len(issues) == 1
    assert issues[0].rule_id == "CARGO-PIN-002"
    assert "my_repo" in issues[0].message


def test_open_ended_range_rule(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "crate-open"
version = "0.1.0"
edition = "2021"

[dependencies]
regex = ">= 1.5"
safe_dep = ">= 1.5, < 2.0"
"""
    })

    proj = parse_project(proj_dir)
    rule = OpenEndedRangeRule()
    issues = rule.check(proj)

    assert len(issues) == 1
    assert issues[0].rule_id == "CARGO-PIN-003"
    assert "regex" in issues[0].message


def test_outdated_and_missing_edition_rules(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[workspace]
members = ["crates/*"]
""",
        "crates/legacy/Cargo.toml": """
[package]
name = "legacy-crate"
version = "0.1.0"
edition = "2018"
""",
        "crates/no_edition/Cargo.toml": """
[package]
name = "no-edition-crate"
version = "0.1.0"
"""
    })

    proj = parse_project(proj_dir)
    edt_rule = OutdatedEditionRule()
    missing_edt_rule = MissingEditionRule()

    edt_issues = edt_rule.check(proj)
    missing_issues = missing_edt_rule.check(proj)

    assert len(edt_issues) == 1
    assert edt_issues[0].rule_id == "CARGO-EDT-001"
    assert "legacy-crate" in edt_issues[0].message

    assert len(missing_issues) == 1
    assert missing_issues[0].rule_id == "CARGO-EDT-002"
    assert "no-edition-crate" in missing_issues[0].message


def test_missing_metadata_rules(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "bare-crate"
version = "0.1.0"
edition = "2021"
"""
    })

    proj = parse_project(proj_dir)

    desc_issues = MissingDescriptionRule().check(proj)
    lic_issues = MissingLicenseRule().check(proj)
    repo_issues = MissingRepositoryRule().check(proj)
    readme_issues = MissingReadmeRule().check(proj)
    msrv_issues = MissingMSRVRule().check(proj)

    assert len(desc_issues) == 1
    assert desc_issues[0].rule_id == "CARGO-META-001"

    assert len(lic_issues) == 1
    assert lic_issues[0].rule_id == "CARGO-META-002"

    assert len(repo_issues) == 1
    assert repo_issues[0].rule_id == "CARGO-META-003"

    assert len(readme_issues) == 1
    assert readme_issues[0].rule_id == "CARGO-META-004"

    assert len(msrv_issues) == 1
    assert msrv_issues[0].rule_id == "CARGO-MSRV-001"


def test_workspace_inheritance_recommendation(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[workspace]
members = ["crates/*"]
""",
        "crates/a/Cargo.toml": """
[package]
name = "crate-a"
version = "0.1.0"
edition = "2021"

[dependencies]
clap = "4.4"
""",
        "crates/b/Cargo.toml": """
[package]
name = "crate-b"
version = "0.1.0"
edition = "2021"

[dependencies]
clap = "4.4"
"""
    })

    proj = parse_project(proj_dir)
    rule = WorkspaceInheritanceRecommendationRule()
    issues = rule.check(proj)

    assert len(issues) == 1
    assert issues[0].rule_id == "CARGO-WS-001"
    assert "clap" in issues[0].message


def test_get_rules_filtering():
    all_rules = get_rules()
    assert len(all_rules) >= 12

    only_edt = get_rules(include_ids_or_names=["CARGO-EDT-001"])
    assert len(only_edt) == 1
    assert only_edt[0].id == "CARGO-EDT-001"

    excluded_edt = get_rules(exclude_ids_or_names=["CARGO-EDT-001"])
    assert not any(r.id == "CARGO-EDT-001" for r in excluded_edt)
