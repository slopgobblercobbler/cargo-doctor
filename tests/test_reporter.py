"""Tests for output reporter and formats."""

from __future__ import annotations

import json
from pathlib import Path
from cargo_doctor.models import FixResult, Issue, ScanResult, Severity
from cargo_doctor.reporter import Reporter


def test_reporter_json():
    reporter = Reporter(use_color=False)
    issue = Issue(
        rule_id="CARGO-PIN-001",
        rule_name="wildcard-dependency",
        severity=Severity.ERROR,
        message="Wildcard found",
        file_path=Path("Cargo.toml"),
        line_number=10,
        fixable=True,
        suggestion="Pin version",
    )

    rendered = reporter.render_issues_json([issue])
    data = json.loads(rendered)
    assert len(data) == 1
    assert data[0]["rule_id"] == "CARGO-PIN-001"
    assert data[0]["severity"] == "error"
    assert data[0]["line_number"] == 10


def test_reporter_print_issues(capsys):
    reporter = Reporter(use_color=False)
    issue = Issue(
        rule_id="CARGO-EDT-001",
        rule_name="outdated-edition",
        severity=Severity.WARNING,
        message="Edition 2018 is outdated",
        file_path=Path("crates/foo/Cargo.toml"),
        line_number=4,
        fixable=True,
        suggestion="Upgrade to 2021",
    )

    reporter.print_issues([issue], format_type="text")
    captured = capsys.readouterr().out
    assert "[WARN]" in captured
    assert "CARGO-EDT-001" in captured
    assert "Edition 2018 is outdated" in captured
    assert "Upgrade to 2021" in captured


def test_reporter_print_scan(capsys):
    reporter = Reporter(use_color=False)
    scan_res = ScanResult(
        project_path=Path("my_proj"),
        is_workspace=True,
        packages_count=3,
        total_dependencies_count=12,
        unique_dependencies_count=8,
        health_score=92,
        grade="A",
        issues=[],
        editions={"2021": 3},
    )

    reporter.print_scan(scan_res, format_type="summary")
    captured = capsys.readouterr().out
    assert "Grade A (92/100)" in captured
    assert "Workspace:           Yes" in captured
    assert "Packages:            3" in captured


def test_reporter_print_fix(capsys):
    reporter = Reporter(use_color=False)
    fix_res = FixResult(
        files_modified=[Path("Cargo.toml")],
        diffs={Path("Cargo.toml"): "--- a/Cargo.toml\n+++ b/Cargo.toml\n@@ -1 +1 @@\n-edition = \"2018\"\n+edition = \"2021\"\n"},
        fixed_issues_count=1,
        dry_run=True,
        details=["Updated edition to 2021"],
    )

    reporter.print_fix(fix_res)
    captured = capsys.readouterr().out
    assert "[DRY RUN]" in captured
    assert "Updated edition to 2021" in captured
    assert "-edition = \"2018\"" in captured
