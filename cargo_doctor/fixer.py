"""Automated autofixer engine for Cargo.toml manifests."""

from __future__ import annotations

import difflib
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from cargo_doctor.models import FixResult, Issue, Project, Severity


class ManifestFixer:
    """Safely applies automated fixes to Cargo.toml files while preserving comments and formatting."""

    def __init__(self, target_edition: str = "2021"):
        self.target_edition = target_edition

    def fix_edition_in_text(self, content: str) -> Tuple[str, bool]:
        """Upgrade outdated edition or insert missing edition under [package]."""
        changed = False
        lines = content.splitlines(keepends=True)

        # Check if edition line exists
        edition_pattern = re.compile(r'^(\s*edition\s*=\s*["\'])(2015|2018)(["\'].*)$')
        new_lines = []
        found_edition = False
        in_package = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                in_package = stripped == "[package]"

            if in_package and not found_edition:
                match = edition_pattern.match(line)
                if match:
                    new_line = f'{match.group(1)}{self.target_edition}{match.group(3)}\n'
                    new_lines.append(new_line)
                    changed = True
                    found_edition = True
                    continue
                elif re.match(r'^\s*edition\s*=', line):
                    found_edition = True

            new_lines.append(line)

        # If [package] exists but edition was completely missing, add it
        if not found_edition:
            result_lines = []
            for line in new_lines:
                result_lines.append(line)
                if line.strip() == "[package]":
                    result_lines.append(f'edition = "{self.target_edition}"\n')
                    changed = True
            new_lines = result_lines

        return "".join(new_lines), changed

    def fix_metadata_in_text(
        self,
        content: str,
        package_name: str,
        missing_fields: Set[str],
    ) -> Tuple[str, bool]:
        """Insert default/template metadata fields under [package]."""
        if not missing_fields:
            return content, False

        lines = content.splitlines(keepends=True)
        new_lines = []
        in_package = False
        inserted = False

        # Prepare fields to insert
        defaults = {
            "description": f'description = "{package_name} implementation"\n',
            "license": 'license = "MIT OR Apache-2.0"\n',
            "readme": 'readme = "README.md"\n',
            "rust-version": 'rust-version = "1.70.0"\n',
        }

        fields_to_add = [defaults[f] for f in missing_fields if f in defaults]
        if not fields_to_add:
            return content, False

        for line in lines:
            new_lines.append(line)
            stripped = line.strip()
            if stripped == "[package]" and not inserted:
                for field_str in fields_to_add:
                    new_lines.append(field_str)
                inserted = True

        return "".join(new_lines), inserted

    def fix_wildcard_in_text(self, content: str, crate_name: str, pin_version: str = "1.0") -> Tuple[str, bool]:
        """Replace wildcard * with pinned version."""
        lines = content.splitlines(keepends=True)
        new_lines = []
        changed = False

        # Pattern: crate = "*" or crate = { ... version = "*" ... }
        # Simple string: tokio = "*" -> tokio = "1.0"
        simple_pattern = re.compile(
            rf'^(\s*{re.escape(crate_name)}\s*=\s*["\'])\*(["\'].*)$'
        )
        # Inline table: tokio = { version = "*", ... }
        table_pattern = re.compile(
            rf'^(\s*{re.escape(crate_name)}\s*=.*version\s*=\s*["\'])\*(["\'].*)$'
        )

        for line in lines:
            match_s = simple_pattern.match(line)
            if match_s:
                new_lines.append(f"{match_s.group(1)}{pin_version}{match_s.group(2)}\n")
                changed = True
                continue

            match_t = table_pattern.match(line)
            if match_t:
                new_lines.append(f"{match_t.group(1)}{pin_version}{match_t.group(2)}\n")
                changed = True
                continue

            new_lines.append(line)

        return "".join(new_lines), changed

    def fix_dependency_version_in_text(
        self,
        content: str,
        crate_name: str,
        target_version: str,
    ) -> Tuple[str, bool]:
        """Standardize dependency version to target_version."""
        lines = content.splitlines(keepends=True)
        new_lines = []
        changed = False

        # Pattern: crate = "old_ver"
        simple_pattern = re.compile(
            rf'^(\s*{re.escape(crate_name)}\s*=\s*["\'])[^"\']+(["\'].*)$'
        )
        # Inline table: crate = { version = "old_ver", ... }
        table_pattern = re.compile(
            rf'^(\s*{re.escape(crate_name)}\s*=.*version\s*=\s*["\'])[^"\']+(["\'].*)$'
        )

        for line in lines:
            # Avoid replacing if line is a different crate or section
            match_s = simple_pattern.match(line)
            if match_s:
                new_lines.append(f"{match_s.group(1)}{target_version}{match_s.group(2)}\n")
                changed = True
                continue

            match_t = table_pattern.match(line)
            if match_t:
                new_lines.append(f"{match_t.group(1)}{target_version}{match_t.group(2)}\n")
                changed = True
                continue

            new_lines.append(line)

        return "".join(new_lines), changed

    def fix_workspace_inheritance_in_text(
        self,
        content: str,
        crate_name: str,
    ) -> Tuple[str, bool]:
        """Convert inline crate definition to workspace = true."""
        lines = content.splitlines(keepends=True)
        new_lines = []
        changed = False

        # Simple string: crate = "1.0" -> crate.workspace = true
        simple_pattern = re.compile(
            rf'^\s*{re.escape(crate_name)}\s*=\s*["\'][^"\']+["\'](\s*(#.*)?)$'
        )
        # Inline table: crate = { version = "1.0", features = ["..."] } -> crate = { workspace = true, features = ["..."] }
        inline_with_features = re.compile(
            rf'^(\s*{re.escape(crate_name)}\s*=\s*\{{)\s*version\s*=\s*["\'][^"\']+["\']\s*,\s*(.*)$'
        )

        for line in lines:
            match_s = simple_pattern.match(line)
            if match_s:
                comment = match_s.group(1) or ""
                new_lines.append(f"{crate_name} = {{ workspace = true }}{comment}\n")
                changed = True
                continue

            match_f = inline_with_features.match(line)
            if match_f:
                new_lines.append(f"{match_f.group(1)} workspace = true, {match_f.group(2)}\n")
                changed = True
                continue

            new_lines.append(line)

        return "".join(new_lines), changed


def apply_fixes(
    project: Project,
    issues: List[Issue],
    dry_run: bool = False,
    backup: bool = False,
    fix_edition: bool = True,
    fix_duplicates: bool = True,
    fix_unpinned: bool = True,
    fix_metadata: bool = True,
    target_edition: str = "2021",
) -> FixResult:
    """Apply autofixes to project files based on detected issues."""
    fixer = ManifestFixer(target_edition=target_edition)
    result = FixResult(dry_run=dry_run)

    # Group issues by file_path
    issues_by_file: Dict[Path, List[Issue]] = {}
    for issue in issues:
        if issue.fixable and issue.file_path:
            issues_by_file.setdefault(issue.file_path, []).append(issue)

    for file_path, file_issues in issues_by_file.items():
        if not file_path.is_file():
            continue

        original_content = file_path.read_text(encoding="utf-8")
        current_content = original_content
        file_fixed_count = 0
        file_details: List[str] = []

        # Find package name if available
        pkg_name = file_path.parent.name
        for pkg in project.all_packages:
            if pkg.manifest_path.resolve() == file_path.resolve():
                pkg_name = pkg.name
                break

        # 1. Edition fix
        if fix_edition:
            edition_issues = [
                i for i in file_issues if i.rule_id in ("CARGO-EDT-001", "CARGO-EDT-002")
            ]
            if edition_issues:
                updated, changed = fixer.fix_edition_in_text(current_content)
                if changed:
                    current_content = updated
                    file_fixed_count += len(edition_issues)
                    file_details.append(
                        f"Updated edition to '{target_edition}' in {file_path.name}"
                    )

        # 2. Metadata fix
        if fix_metadata:
            meta_issues = [
                i for i in file_issues if i.rule_id.startswith("CARGO-META-") or i.rule_id == "CARGO-MSRV-001"
            ]
            if meta_issues:
                fields_to_add: Set[str] = set()
                for mi in meta_issues:
                    f = mi.context.get("field")
                    if f:
                        fields_to_add.add(f)
                if fields_to_add:
                    updated, changed = fixer.fix_metadata_in_text(
                        current_content, pkg_name, fields_to_add
                    )
                    if changed:
                        current_content = updated
                        file_fixed_count += len(meta_issues)
                        file_details.append(
                            f"Added missing metadata ({', '.join(sorted(fields_to_add))}) in {file_path.name}"
                        )

        # 3. Duplicate & Workspace Dependency fix
        if fix_duplicates:
            dup_issues = [i for i in file_issues if i.rule_id == "CARGO-DUP-001"]
            for di in dup_issues:
                crate = di.context.get("crate")
                target_ver = di.context.get("target_version")
                if crate and target_ver:
                    updated, changed = fixer.fix_dependency_version_in_text(
                        current_content, crate, target_ver
                    )
                    if changed:
                        current_content = updated
                        file_fixed_count += 1
                        file_details.append(
                            f"Aligned '{crate}' to version '{target_ver}' in {file_path.name}"
                        )

            ws_issues = [i for i in file_issues if i.rule_id == "CARGO-DUP-002"]
            for wi in ws_issues:
                crate = wi.context.get("crate")
                if crate:
                    updated, changed = fixer.fix_workspace_inheritance_in_text(
                        current_content, crate
                    )
                    if changed:
                        current_content = updated
                        file_fixed_count += 1
                        file_details.append(
                            f"Converted '{crate}' to inherit from workspace in {file_path.name}"
                        )

        # 4. Unpinned wildcard fix
        if fix_unpinned:
            pin_issues = [i for i in file_issues if i.rule_id == "CARGO-PIN-001"]
            for pi in pin_issues:
                crate = pi.context.get("crate")
                if crate:
                    # Look up if another package has a specific version for this crate
                    target_ver = "1.0"
                    for p in project.all_packages:
                        for d in p.dependencies:
                            if d.name == crate and d.version and "*" not in d.version:
                                target_ver = d.version
                                break
                    updated, changed = fixer.fix_wildcard_in_text(
                        current_content, crate, target_ver
                    )
                    if changed:
                        current_content = updated
                        file_fixed_count += 1
                        file_details.append(
                            f"Pinned wildcard '{crate}' to '{target_ver}' in {file_path.name}"
                        )

        # If content changed, record diff and optionally write
        if current_content != original_content:
            diff = "".join(
                difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    current_content.splitlines(keepends=True),
                    fromfile=f"a/{file_path.name}",
                    tofile=f"b/{file_path.name}",
                )
            )
            result.diffs[file_path] = diff
            result.files_modified.append(file_path)
            result.fixed_issues_count += file_fixed_count
            result.details.extend(file_details)

            if not dry_run:
                if backup:
                    bak_file = file_path.with_suffix(".toml.bak")
                    shutil.copy2(file_path, bak_file)
                file_path.write_text(current_content, encoding="utf-8")

    return result
