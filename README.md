# cargo-doctor 🦀🩺

[![CI](https://github.com/slopgobblercobbler/cargo-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/slopgobblercobbler/cargo-doctor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> **Production-grade linter, duplicate detector, health auditor, and autofixer for Rust `Cargo.toml` manifests and multi-crate workspaces.**

`cargo-doctor` inspects, audits, scores, and repairs `Cargo.toml` manifests across individual crates and complex multi-crate Rust workspaces. It detects duplicate and mismatched dependency versions across workspace members, warns on unsafe wildcard or unpinned git dependencies, flags outdated Rust editions, audits missing package metadata, and automatically fixes manifests in-place with zero configuration.

---

## Features

- 🦀 **Rust Workspace Intelligence**:
  - Automatically discovers virtual and package workspaces, traversing member globs (`crates/*`, `packages/**`) and respecting exclusions.
  - Detects **conflicting dependency versions** across workspace members that cause duplicate compilation and binary bloat (`CARGO-DUP-001`).
  - Identifies **workspace inheritance opportunities** (`CARGO-DUP-002`, `CARGO-WS-001`) to consolidate redundant definitions into `[workspace.dependencies]`.
- 🔍 **Metadata Audit & Crates.io Readiness**:
  - Audits packages for missing `description` (`CARGO-META-001`), `license` / `license-file` (`CARGO-META-002`), `repository` URL (`CARGO-META-003`), `readme` (`CARGO-META-004`), and `rust-version` MSRV (`CARGO-MSRV-001`).
  - Escalates severity based on whether a crate is publishable (`publish = false` respected).
- 🛡️ **Version Specifier Sanity**:
  - Catches wildcard dependencies `*` (`CARGO-PIN-001`) that break reproducibility and fail on crates.io.
  - Warns on unpinned git dependencies lacking an immutable `rev` or `tag` (`CARGO-PIN-002`).
  - Warns on open-ended inequality version bounds (`>= 1.0`) without an upper bound (`CARGO-PIN-003`).
- ⚡ **Auto-Fixer (`fix`)**:
  - Upgrades obsolete editions (2015/2018) to modern `edition = "2021"` or `2024`.
  - Replaces wildcard `*` with pinned semantic versions.
  - Generates template metadata fields for missing description, license, readme, and MSRV.
  - Consolidates duplicated member dependencies into workspace inheritance (`workspace = true`).
  - Supports `--dry-run` with unified diff preview and `--backup` (`.toml.bak`).
- 📊 **Health Scoring & CI Integration**:
  - `scan` command calculates an overall project health score (0-100) and letter grade (A through F).
  - Terminal table formatting, plain text for pipes, and `--json` for automated tooling.
  - `--strict` mode to enforce zero warnings or minimum health threshold in CI pipelines.

---

## Installation

### Via pip
```bash
pip install cargo-doctor
```

### From source
```bash
git clone https://github.com/slopgobblercobbler/cargo-doctor.git
cd cargo-doctor
pip install -e .
```

---

## Quick Start

### 1. Check your project
Run `cargo-doctor check` in any crate or workspace directory:

```bash
cargo-doctor check
```

### 2. Check in CI mode (fail on issues)
Use `--strict` to return exit code `1` if any lint issues or warnings exist:

```bash
cargo-doctor check --strict
```

### 3. Scan project health score
Calculate the project health grade and dependency metrics:

```bash
cargo-doctor scan
```

### 4. Preview fixes with diff
View the unified diff of what `fix` would modify without writing changes to disk:

```bash
cargo-doctor fix --dry-run
```

### 5. Auto-fix manifests in place
Automatically upgrade editions, pin wildcards, and insert missing metadata:

```bash
cargo-doctor fix --all
```

### 6. Output JSON report
Emit structured JSON diagnostics:

```bash
cargo-doctor check --json
cargo-doctor scan --json
```

---

## Diagnostic Rules Catalog

| Rule ID | Rule Name | Default Severity | Auto-Fixable | Description |
|:---|:---|:---:|:---:|:---|
| `CARGO-DUP-001` | `duplicate-dependency-versions` | **WARNING** | **Yes** | Conflicting or mismatched versions of the same dependency across workspace members. |
| `CARGO-DUP-002` | `uninherited-workspace-dependency` | **WARNING** | **Yes** | Dependency defined in `[workspace.dependencies]` is duplicated inline in a member instead of using `workspace = true`. |
| `CARGO-PIN-001` | `wildcard-dependency` | **ERROR** | **Yes** | Wildcard version requirement `*` that breaks build reproducibility and crates.io publishing. |
| `CARGO-PIN-002` | `unpinned-git-dependency` | **WARNING** | No | Git dependency without an immutable `rev` (commit SHA) or `tag`. |
| `CARGO-PIN-003` | `open-ended-range` | **WARNING** | No | Inequality version bound (e.g. `>= 1.0`) without an upper bound. |
| `CARGO-EDT-001` | `outdated-edition` | **WARNING** | **Yes** | Manifest uses legacy Rust edition (`2015` or `2018`). |
| `CARGO-EDT-002` | `missing-edition` | **WARNING** | **Yes** | Package missing an explicit `edition` key (Cargo defaults to legacy 2015). |
| `CARGO-META-001` | `missing-description` | **WARNING** | **Yes** | Package missing `description` in `[package]` table. |
| `CARGO-META-002` | `missing-license` | **WARNING** | **Yes** | Package missing `license` or `license-file` declaration. |
| `CARGO-META-003` | `missing-repository` | **SUGGESTION** | No | Package missing source `repository` URL. |
| `CARGO-META-004` | `missing-readme` | **SUGGESTION** | **Yes** | Package missing `readme` path specification. |
| `CARGO-MSRV-001` | `missing-rust-version` | **SUGGESTION** | **Yes** | Package does not declare Minimum Supported Rust Version (`rust-version`). |
| `CARGO-WS-001` | `recommend-workspace-dependencies` | **SUGGESTION** | No | Common dependency used across 2+ workspace members recommended for hoisting to `[workspace.dependencies]`. |

---

## CLI Commands & Options

### `cargo-doctor check`
Inspects Cargo manifests for duplicate dependencies, unpinned crates, outdated editions, and missing metadata.

```bash
cargo-doctor check [PATH] [OPTIONS]
```

| Flag | Default | Description |
|---|---|---|
| `PATH` | `.` | Path to `Cargo.toml` or directory containing manifests. |
| `--strict` | `False` | Exit with code `1` on warnings or suggestions, not just errors. |
| `--rule RULE` | None | Run only specified rule IDs or names (repeatable or comma-separated). |
| `--ignore RULE` | None | Ignore specified rule IDs or names (repeatable or comma-separated). |
| `--format` | `table` | Output format: `table`, `text`, or `json`. |
| `--json` | `False` | Shortcut for `--format json`. |
| `-q, --quiet` | `False` | Suppress non-error informational messages. |
| `--no-color` | `False` | Disable ANSI color codes. |

---

### `cargo-doctor fix`
Automatically repairs detected issues in `Cargo.toml` files.

```bash
cargo-doctor fix [PATH] [OPTIONS]
```

| Flag | Default | Description |
|---|---|---|
| `PATH` | `.` | Path to `Cargo.toml` or directory containing manifests. |
| `--dry-run` | `False` | Show diffs of proposed changes without writing files to disk. |
| `--all` | `False` | Apply all available automated fixes. |
| `-e, --fix-edition` | `False` | Upgrade outdated editions to target edition. |
| `-d, --fix-duplicates` | `False` | Standardize duplicate dependency versions across workspace. |
| `-u, --fix-unpinned` | `False` | Pin wildcard `*` dependencies. |
| `-m, --fix-metadata` | `False` | Insert missing package metadata template fields. |
| `--target-edition` | `2021` | Target Rust edition (`2021` or `2024`). |
| `--backup` | `False` | Create backup files (`.toml.bak`) before modifying. |
| `--rule RULE` | None | Filter fixes to specific rules. |
| `--ignore RULE` | None | Ignore specific rules during fix. |

---

### `cargo-doctor scan`
Calculates project health score (0-100), metrics, and letter grade overview.

```bash
cargo-doctor scan [PATH] [OPTIONS]
```

| Flag | Default | Description |
|---|---|---|
| `PATH` | `.` | Path to project root. |
| `--format` | `summary` | Output format: `summary`, `table`, or `json`. |
| `--json` | `False` | Output scan diagnostics as JSON. |
| `--strict` | `False` | Fail if health score is below threshold or errors exist. |
| `--min-score` | `80` | Minimum required health score when using `--strict`. |

---

## GitHub Actions CI Workflow

Add `cargo-doctor` to your Rust project's CI pipeline:

```yaml
name: Manifest Hygiene

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  cargo-doctor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install cargo-doctor
        run: pip install cargo-doctor
      - name: Audit Cargo.toml manifests
        run: cargo-doctor check --strict
```

---

## Python Library API

`cargo-doctor` provides a full Python API for custom tooling and script integration:

```python
from cargo_doctor import CargoDoctor, inspect_project, fix_project, scan_project

# 1. Inspect manifests for issues
issues = inspect_project(path=".", strict=False)
for issue in issues:
    print(f"[{issue.severity.value}] {issue.rule_id} ({issue.file_path}): {issue.message}")

# 2. Scan project health metrics
scan_res = scan_project(path=".")
print(f"Project Grade: {scan_res.grade} ({scan_res.health_score}/100)")
print(f"Unique Dependencies: {scan_res.unique_dependencies_count}")

# 3. Apply fixes programmatically
fix_res = fix_project(path=".", dry_run=True)
for detail in fix_res.details:
    print(detail)
```

---

## Contributing

Contributions, feature suggestions, and bug reports are welcome!
1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/my-enhancement`).
3. Run the test suite: `pytest -v`.
4. Commit your changes and open a Pull Request.

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
Copyright (c) 2026 slopggobblercobbler81.
