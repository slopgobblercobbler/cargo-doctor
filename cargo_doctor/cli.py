"""Command line interface for cargo-doctor."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from cargo_doctor import __version__
from cargo_doctor.models import Severity
from cargo_doctor.reporter import Reporter
from cargo_doctor.scanner import CargoDoctor


def parse_list_arg(arg_val: Optional[List[str]]) -> Optional[List[str]]:
    """Flatten comma-separated or multi-value arguments."""
    if not arg_val:
        return None
    res = []
    for item in arg_val:
        for part in item.split(","):
            part_s = part.strip()
            if part_s:
                res.append(part_s)
    return res if res else None


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color output.",
    )
    common_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )

    parser = argparse.ArgumentParser(
        prog="cargo-doctor",
        parents=[common_parser],
        description="Cargo Doctor: Production-grade linter, duplicate detector, and autofixer for Rust Cargo.toml and workspace manifests.",
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: check
    check_parser = subparsers.add_parser(
        "check",
        parents=[common_parser],
        help="Inspect Cargo manifests for duplicate dependencies, unpinned crates, outdated editions, and missing metadata.",
    )
    check_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to Cargo.toml or directory containing Cargo.toml (default: current directory).",
    )
    check_parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail (exit 1) on any warnings or suggestions, not just errors.",
    )
    check_parser.add_argument(
        "--rule",
        action="append",
        help="Run only specified rule IDs or names (can be repeated or comma-separated).",
    )
    check_parser.add_argument(
        "--ignore",
        action="append",
        help="Ignore specified rule IDs or names (can be repeated or comma-separated).",
    )
    check_parser.add_argument(
        "--format",
        choices=["table", "text", "json"],
        default="table",
        help="Output format (default: table).",
    )
    check_parser.add_argument(
        "--json",
        action="store_true",
        help="Shortcut for --format json.",
    )
    check_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Quiet mode: suppress informational output.",
    )

    # Command: fix
    fix_parser = subparsers.add_parser(
        "fix",
        parents=[common_parser],
        help="Automatically fix detected issues in Cargo.toml files.",
    )
    fix_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to Cargo.toml or directory containing Cargo.toml (default: current directory).",
    )
    fix_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show diffs of proposed changes without modifying files on disk.",
    )
    fix_parser.add_argument(
        "--all",
        action="store_true",
        help="Apply all available automated fixes (edition, duplicates, unpinned, metadata).",
    )
    fix_parser.add_argument(
        "-e",
        "--fix-edition",
        action="store_true",
        help="Upgrade outdated editions to target edition (default: 2021).",
    )
    fix_parser.add_argument(
        "-d",
        "--fix-duplicates",
        action="store_true",
        help="Standardize duplicate dependency versions across workspace.",
    )
    fix_parser.add_argument(
        "-u",
        "--fix-unpinned",
        action="store_true",
        help="Pin wildcard '*' dependencies.",
    )
    fix_parser.add_argument(
        "-m",
        "--fix-metadata",
        action="store_true",
        help="Insert missing package metadata template fields.",
    )
    fix_parser.add_argument(
        "--target-edition",
        default="2021",
        choices=["2021", "2024"],
        help="Target Rust edition for fixes (default: 2021).",
    )
    fix_parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup files (.toml.bak) before modifying.",
    )
    fix_parser.add_argument(
        "--rule",
        action="append",
        help="Filter fixes to specific rules.",
    )
    fix_parser.add_argument(
        "--ignore",
        action="append",
        help="Ignore specific rules during fix.",
    )

    # Command: scan
    scan_parser = subparsers.add_parser(
        "scan",
        parents=[common_parser],
        help="Scan project health, calculate health score, and display metrics overview.",
    )
    scan_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to Cargo.toml or directory containing Cargo.toml (default: current directory).",
    )
    scan_parser.add_argument(
        "--format",
        choices=["summary", "table", "json"],
        default="summary",
        help="Output format (default: summary).",
    )
    scan_parser.add_argument(
        "--json",
        action="store_true",
        help="Shortcut for --format json.",
    )
    scan_parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if health score is below threshold or any errors exist.",
    )
    scan_parser.add_argument(
        "--min-score",
        type=int,
        default=80,
        help="Minimum required health score when using --strict (default: 80).",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    reporter = Reporter(use_color=not args.no_color)

    try:
        if args.command == "check":
            rules_filter = parse_list_arg(args.rule)
            ignore_filter = parse_list_arg(args.ignore)
            doctor = CargoDoctor(
                include_rules=rules_filter,
                exclude_rules=ignore_filter,
            )

            issues = doctor.inspect(args.path)
            fmt = "json" if args.json else args.format

            if not args.quiet:
                reporter.print_issues(issues, format_type=fmt)

            has_errors = any(i.severity == Severity.ERROR for i in issues)
            has_warnings = any(i.severity == Severity.WARNING for i in issues)

            if has_errors:
                return 1
            if args.strict and (has_warnings or len(issues) > 0):
                return 1
            return 0

        elif args.command == "fix":
            # If no specific fix flag specified, default to --all
            fix_all = args.all or not (
                args.fix_edition or args.fix_duplicates or args.fix_unpinned or args.fix_metadata
            )
            fix_edition = args.fix_edition or fix_all
            fix_duplicates = args.fix_duplicates or fix_all
            fix_unpinned = args.fix_unpinned or fix_all
            fix_metadata = args.fix_metadata or fix_all

            rules_filter = parse_list_arg(args.rule)
            ignore_filter = parse_list_arg(args.ignore)
            doctor = CargoDoctor(
                target_edition=args.target_edition,
                include_rules=rules_filter,
                exclude_rules=ignore_filter,
            )

            result = doctor.fix(
                path=args.path,
                dry_run=args.dry_run,
                backup=args.backup,
                fix_edition=fix_edition,
                fix_duplicates=fix_duplicates,
                fix_unpinned=fix_unpinned,
                fix_metadata=fix_metadata,
            )

            reporter.print_fix(result)
            return 0

        elif args.command == "scan":
            doctor = CargoDoctor()
            scan_res = doctor.scan(args.path)
            fmt = "json" if args.json else args.format

            reporter.print_scan(scan_res, format_type=fmt)

            if args.strict:
                if scan_res.errors_count > 0 or scan_res.health_score < args.min_score:
                    return 1
            return 0

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
