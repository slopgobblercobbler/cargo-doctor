"""Tests for cargo-doctor CLI commands and exit codes."""

from __future__ import annotations

from cargo_doctor.cli import main


def test_cli_version(capsys):
    try:
        main(["--version"])
    except SystemExit as e:
        assert e.code == 0
    captured = capsys.readouterr().out
    assert "cargo-doctor 0.1.0" in captured


def test_cli_no_args(capsys):
    ret = main([])
    assert ret == 0
    captured = capsys.readouterr().out
    assert "usage: cargo-doctor" in captured


def test_cli_check_healthy(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "healthy"
version = "0.1.0"
edition = "2021"
description = "Clean crate"
license = "MIT"
repository = "https://github.com/foo/bar"
readme = "README.md"
rust-version = "1.70.0"

[dependencies]
serde = "1.0"
"""
    })

    ret = main(["check", str(proj_dir), "--no-color"])
    assert ret == 0


def test_cli_check_with_error(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "bad-crate"
version = "0.1.0"
edition = "2021"

[dependencies]
wildcard_crate = "*"
"""
    })

    ret = main(["check", str(proj_dir), "--no-color"])
    assert ret == 1


def test_cli_check_strict_with_warning(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "warn-crate"
version = "0.1.0"
edition = "2018"
description = "Has outdated edition"
license = "MIT"
readme = "README.md"
repository = "https://github.com/foo/bar"
rust-version = "1.70.0"
"""
    })

    # Without strict, warnings don't fail
    ret_normal = main(["check", str(proj_dir), "--no-color"])
    assert ret_normal == 0

    # With strict, warnings fail with code 1
    ret_strict = main(["check", "--strict", str(proj_dir), "--no-color"])
    assert ret_strict == 1


def test_cli_check_rule_filtering(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "filtered"
version = "0.1.0"
edition = "2018"

[dependencies]
broken = "*"
"""
    })

    # If we only check CARGO-EDT-001 (warning only), exit code is 0 without --strict
    ret = main(["check", "--rule", "CARGO-EDT-001", str(proj_dir), "--no-color"])
    assert ret == 0

    # If we ignore wildcard rule CARGO-PIN-001
    ret_ign = main(["check", "--ignore", "CARGO-PIN-001", str(proj_dir), "--no-color"])
    assert ret_ign == 0


def test_cli_scan(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "scanned"
version = "0.1.0"
edition = "2021"
description = "A scanned crate"
license = "MIT"
readme = "README.md"
repository = "https://github.com/foo/bar"
rust-version = "1.70.0"
"""
    })

    ret = main(["scan", str(proj_dir), "--no-color"])
    assert ret == 0

    ret_json = main(["scan", "--json", str(proj_dir)])
    assert ret_json == 0


def test_cli_scan_strict_fail(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "low-score"
version = "0.1.0"

[dependencies]
bad1 = "*"
bad2 = "*"
"""
    })

    # Health score will be low and errors present
    ret = main(["scan", "--strict", str(proj_dir), "--no-color"])
    assert ret == 1


def test_cli_fix_dry_run_and_apply(temp_project):
    proj_dir = temp_project({
        "Cargo.toml": """
[package]
name = "fixable"
version = "0.1.0"
edition = "2018"
"""
    })

    # Dry run
    ret_dry = main(["fix", "--dry-run", str(proj_dir), "--no-color"])
    assert ret_dry == 0
    content_dry = (proj_dir / "Cargo.toml").read_text(encoding="utf-8")
    assert 'edition = "2018"' in content_dry

    # Apply all fixes
    ret_apply = main(["fix", "--all", str(proj_dir), "--no-color"])
    assert ret_apply == 0
    content_applied = (proj_dir / "Cargo.toml").read_text(encoding="utf-8")
    assert 'edition = "2021"' in content_applied
    assert 'license = "MIT OR Apache-2.0"' in content_applied


def test_cli_nonexistent_path():
    ret = main(["check", "non_existent_dir_999999", "--no-color"])
    assert ret == 2
