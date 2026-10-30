"""Output formatting and reporting for cargo-doctor."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from cargo_doctor.models import FixResult, Issue, ScanResult, Severity


class Reporter:
    """Handles rendering scan results and diagnostics in various formats."""

    def __init__(self, use_color: bool = True):
        self.use_color = use_color and sys.stdout.isatty() if not hasattr(sys.stdout, "isatty") or sys.stdout.isatty() else use_color
        if RICH_AVAILABLE:
            self.console = Console(no_color=not use_color)
        else:
            self.console = None

    def render_issues_json(self, issues: List[Issue]) -> str:
        """Render issues list as JSON."""
        return json.dumps([issue.to_dict() for issue in issues], indent=2)

    def render_scan_json(self, scan_result: ScanResult) -> str:
        """Render scan result as JSON."""
        return json.dumps(scan_result.to_dict(), indent=2)

    def print_issues(self, issues: List[Issue], format_type: str = "text") -> None:
        """Display list of issues in terminal."""
        if format_type == "json":
            print(self.render_issues_json(issues))
            return

        if not issues:
            if self.console and self.use_color:
                self.console.print("[bold green]✓ No issues found. Cargo manifest is healthy![/bold green]")
            else:
                print("✓ No issues found. Cargo manifest is healthy!")
            return

        if format_type == "table" and self.console:
            table = Table(title="Cargo Doctor Diagnostics", show_lines=True)
            table.add_column("Severity", style="bold", width=10)
            table.add_column("Rule", style="cyan", width=16)
            table.add_column("File:Line", style="magenta", width=25)
            table.add_column("Message", style="white")
            table.add_column("Fixable", style="green", width=8)

            for issue in issues:
                loc = f"{Path(issue.file_path).name}"
                if issue.line_number:
                    loc += f":{issue.line_number}"

                fix_str = "Yes" if issue.fixable else "No"
                color = issue.severity.color
                table.add_row(
                    f"[{color}]{issue.severity.value.upper()}[/{color}]",
                    issue.rule_name,
                    loc,
                    issue.message + (f"\n[dim]Suggestion: {issue.suggestion}[/dim]" if issue.suggestion else ""),
                    fix_str,
                )

            self.console.print(table)
            return

        # Plain text rendering
        for issue in issues:
            loc = f"{issue.file_path}"
            if issue.line_number:
                loc += f":{issue.line_number}"

            badge = issue.severity.badge
            print(f"{badge} {loc} [{issue.rule_id} {issue.rule_name}]")
            print(f"  Message: {issue.message}")
            if issue.suggestion:
                print(f"  Suggestion: {issue.suggestion}")
            print()

        # Summary line
        errors = sum(1 for i in issues if i.severity == Severity.ERROR)
        warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
        suggs = sum(1 for i in issues if i.severity in (Severity.SUGGESTION, Severity.INFO))
        print(f"Total: {len(issues)} issues ({errors} errors, {warnings} warnings, {suggs} suggestions)")

    def print_scan(self, scan_result: ScanResult, format_type: str = "summary") -> None:
        """Display scan result in terminal."""
        if format_type == "json":
            print(self.render_scan_json(scan_result))
            return

        if self.console and self.use_color:
            # Rich summary card
            score_color = "green" if scan_result.health_score >= 80 else ("yellow" if scan_result.health_score >= 50 else "red")
            title = f"Cargo Doctor Project Health Report (Grade: {scan_result.grade})"
            
            summary_text = (
                f"[bold]Root Path:[/bold] {scan_result.project_path}\n"
                f"[bold]Workspace:[/bold] {'Yes' if scan_result.is_workspace else 'No'}\n"
                f"[bold]Packages:[/bold] {scan_result.packages_count}\n"
                f"[bold]Unique Dependencies:[/bold] {scan_result.unique_dependencies_count} "
                f"({scan_result.total_dependencies_count} total occurrences)\n"
                f"[bold]Health Score:[/bold] [{score_color}]{scan_result.health_score}/100[/{score_color}] "
                f"([bold {score_color}]Grade {scan_result.grade}[/bold {score_color}])\n"
                f"[bold]Diagnostics:[/bold] [red]{scan_result.errors_count} errors[/red], "
                f"[yellow]{scan_result.warnings_count} warnings[/yellow], "
                f"[cyan]{scan_result.suggestions_count} suggestions[/cyan] "
                f"([green]{scan_result.fixable_count} autofixable[/green])\n"
            )

            if scan_result.editions:
                ed_str = ", ".join(f"{k}: {v}" for k, v in sorted(scan_result.editions.items()))
                summary_text += f"[bold]Rust Editions:[/bold] {ed_str}\n"

            self.console.print(Panel(summary_text, title=title, border_style=score_color))
        else:
            print("=" * 60)
            print(f" Cargo Doctor Project Health Report - Grade {scan_result.grade} ({scan_result.health_score}/100)")
            print("=" * 60)
            print(f"Path:                {scan_result.project_path}")
            print(f"Workspace:           {'Yes' if scan_result.is_workspace else 'No'}")
            print(f"Packages:            {scan_result.packages_count}")
            print(f"Dependencies:        {scan_result.unique_dependencies_count} unique ({scan_result.total_dependencies_count} total)")
            print(f"Issues:              {scan_result.errors_count} errors, {scan_result.warnings_count} warnings, {scan_result.suggestions_count} suggestions ({scan_result.fixable_count} fixable)")
            if scan_result.editions:
                ed_str = ", ".join(f"{k}: {v}" for k, v in sorted(scan_result.editions.items()))
                print(f"Editions:            {ed_str}")
            print("=" * 60)

        # Print detailed issues if any
        if scan_result.issues:
            print()
            self.print_issues(scan_result.issues, format_type=format_type)

    def print_fix(self, fix_result: FixResult) -> None:
        """Display fix results and unified diffs."""
        if not fix_result.files_modified:
            if self.console and self.use_color:
                self.console.print("[bold green]✓ No fixable issues found. Everything is up to date![/bold green]")
            else:
                print("✓ No fixable issues found. Everything is up to date!")
            return

        mode_str = "[DRY RUN] " if fix_result.dry_run else ""
        print(f"{mode_str}Applied {fix_result.fixed_issues_count} fixes across {len(fix_result.files_modified)} file(s):")
        for detail in fix_result.details:
            print(f"  - {detail}")

        print()
        # Print unified diffs
        for path, diff in fix_result.diffs.items():
            print(f"--- Diffs for {path} ---")
            print(diff)

        if fix_result.dry_run:
            print("[DRY RUN] No files were written to disk. Re-run without --dry-run to apply changes.")
        else:
            print("✓ Successfully updated manifest files.")
