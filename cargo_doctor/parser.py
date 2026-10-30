"""Parser for Cargo.toml manifests and workspace structures."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        import toml as tomllib  # type: ignore[no-redef]

from cargo_doctor.models import Dependency, Package, Project, Workspace


def load_toml(content_or_path: Union[str, Path]) -> Dict[str, Any]:
    """Load and parse TOML content or file."""
    if isinstance(content_or_path, Path):
        content = content_or_path.read_text(encoding="utf-8")
    else:
        content = content_or_path

    if hasattr(tomllib, "loads"):
        return tomllib.loads(content)
    elif hasattr(tomllib, "loads"):  # toml module
        return tomllib.loads(content)
    raise RuntimeError("No suitable TOML parser available.")


def find_line_number(
    lines: List[str],
    section: Optional[str] = None,
    key: Optional[str] = None,
    value_substr: Optional[str] = None,
) -> Optional[int]:
    """Find 1-indexed line number in TOML file matching section and/or key."""
    current_section = None

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue

        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped.strip("[]").strip()
            if section and current_section == section and key is None:
                return idx
            continue

        if section is None or current_section == section:
            if key and "=" in stripped:
                k = stripped.split("=", 1)[0].strip().strip('"\'')
                if k == key:
                    if value_substr:
                        if value_substr in stripped:
                            return idx
                    else:
                        return idx

    # Fallback search if section was nested or dotted key
    if key:
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "=" in stripped:
                k = stripped.split("=", 1)[0].strip().strip('"\'')
                if k == key:
                    if value_substr:
                        if value_substr in stripped:
                            return idx
                    else:
                        return idx
            elif stripped.startswith(f"[{key}]") or stripped.endswith(f".{key}]"):
                return idx

    return None


def parse_dependency(
    name: str,
    spec: Union[str, Dict[str, Any]],
    section: str = "dependencies",
    target: Optional[str] = None,
    manifest_path: Optional[Path] = None,
    lines: Optional[List[str]] = None,
) -> Dependency:
    """Parse a dependency entry from a Cargo.toml manifest."""
    line_number = None
    if lines and manifest_path:
        # Try to locate dependency line number
        sec_name = f"target.{target}.{section}" if target else section
        line_number = find_line_number(lines, section=sec_name, key=name)
        if line_number is None:
            # Maybe table format [dependencies.name]
            sec_table = f"{section}.{name}" if not target else f"target.{target}.{section}.{name}"
            line_number = find_line_number(lines, section=sec_table)
            if line_number is None:
                line_number = find_line_number(lines, key=name)

    if isinstance(spec, str):
        return Dependency(
            name=name,
            spec=spec,
            version=spec,
            section=section,
            target=target,
            manifest_path=manifest_path,
            line_number=line_number,
        )

    if isinstance(spec, dict):
        version = spec.get("version")
        path = spec.get("path")
        git = spec.get("git")
        branch = spec.get("branch")
        tag = spec.get("tag")
        rev = spec.get("rev")
        workspace = spec.get("workspace", False)
        features = spec.get("features", [])
        if isinstance(features, str):
            features = [features]
        optional = spec.get("optional", False)
        default_features = spec.get("default-features")

        return Dependency(
            name=name,
            spec=spec,
            version=version,
            path=path,
            git=git,
            branch=branch,
            tag=tag,
            rev=rev,
            workspace=bool(workspace),
            features=list(features),
            optional=bool(optional),
            default_features=default_features,
            section=section,
            target=target,
            manifest_path=manifest_path,
            line_number=line_number,
        )

    return Dependency(
        name=name,
        spec=spec,
        section=section,
        target=target,
        manifest_path=manifest_path,
        line_number=line_number,
    )


def extract_dependencies(
    data: Dict[str, Any],
    manifest_path: Optional[Path] = None,
    lines: Optional[List[str]] = None,
) -> List[Dependency]:
    """Extract all dependencies from a manifest data dictionary."""
    deps: List[Dependency] = []
    dep_sections = ["dependencies", "dev-dependencies", "build-dependencies"]

    # 1. Standard sections
    for sec in dep_sections:
        sec_data = data.get(sec, {})
        if isinstance(sec_data, dict):
            for name, spec in sec_data.items():
                deps.append(
                    parse_dependency(
                        name=name,
                        spec=spec,
                        section=sec,
                        manifest_path=manifest_path,
                        lines=lines,
                    )
                )

    # 2. Target specific dependencies: [target.'cfg(...)'.dependencies]
    targets = data.get("target", {})
    if isinstance(targets, dict):
        for target_name, target_content in targets.items():
            if not isinstance(target_content, dict):
                continue
            for sec in dep_sections:
                sec_data = target_content.get(sec, {})
                if isinstance(sec_data, dict):
                    for name, spec in sec_data.items():
                        deps.append(
                            parse_dependency(
                                name=name,
                                spec=spec,
                                section=sec,
                                target=target_name,
                                manifest_path=manifest_path,
                                lines=lines,
                            )
                        )

    return deps


def parse_package(manifest_path: Path) -> Package:
    """Parse a single package from a Cargo.toml file."""
    content = manifest_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    data = load_toml(content)

    pkg_data = data.get("package", {})
    name = pkg_data.get("name", manifest_path.parent.name)
    version = pkg_data.get("version", "0.0.0")
    edition = pkg_data.get("edition")
    description = pkg_data.get("description")
    license_val = pkg_data.get("license")
    license_file = pkg_data.get("license-file")
    repository = pkg_data.get("repository")
    homepage = pkg_data.get("homepage")
    readme = pkg_data.get("readme")
    rust_version = pkg_data.get("rust-version")

    # Arrays
    keywords = pkg_data.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [keywords]
    categories = pkg_data.get("categories", [])
    if isinstance(categories, str):
        categories = [categories]
    authors = pkg_data.get("authors", [])
    if isinstance(authors, str):
        authors = [authors]

    publish = pkg_data.get("publish", True)

    dependencies = extract_dependencies(data, manifest_path=manifest_path, lines=lines)

    return Package(
        name=name,
        version=version,
        manifest_path=manifest_path,
        edition=edition,
        description=description,
        license=license_val,
        license_file=license_file,
        repository=repository,
        homepage=homepage,
        readme=readme,
        keywords=keywords,
        categories=categories,
        authors=authors,
        rust_version=rust_version,
        publish=publish,
        dependencies=dependencies,
        raw_data=data,
    )


def match_exclude(rel_path: str, exclude_patterns: List[str]) -> bool:
    """Check if relative path matches any exclude pattern."""
    normalized = rel_path.replace("\\", "/")
    for pattern in exclude_patterns:
        norm_pattern = pattern.replace("\\", "/").rstrip("/")
        if fnmatch.fnmatch(normalized, norm_pattern):
            return True
        if fnmatch.fnmatch(normalized, f"{norm_pattern}/*"):
            return True
        if normalized == norm_pattern:
            return True
    return False


def discover_workspace_members(
    root_path: Path,
    member_patterns: List[str],
    exclude_patterns: List[str],
) -> List[Path]:
    """Find all member Cargo.toml manifest paths matching workspace patterns."""
    found_manifests: List[Path] = []
    seen: set[Path] = set()

    for pattern in member_patterns:
        # Handle simple glob patterns
        norm_pattern = pattern.replace("\\", "/")
        # If pattern points directly to directory or glob
        matched_paths = list(root_path.glob(norm_pattern))
        for p in matched_paths:
            if not p.is_dir():
                continue
            manifest = p / "Cargo.toml"
            if manifest.is_file():
                try:
                    rel = p.relative_to(root_path).as_posix()
                except ValueError:
                    rel = str(p)

                if match_exclude(rel, exclude_patterns):
                    continue

                resolved = manifest.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    found_manifests.append(manifest)

    return sorted(found_manifests)


def parse_project(path_or_dir: Union[str, Path]) -> Project:
    """Parse a project path (Cargo.toml or directory containing Cargo.toml)."""
    p = Path(path_or_dir).resolve()
    if p.is_file() and p.name == "Cargo.toml":
        manifest_path = p
        root_dir = p.parent
    elif p.is_dir():
        manifest_path = p / "Cargo.toml"
        root_dir = p
    else:
        raise FileNotFoundError(f"Cargo.toml not found at {p}")

    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    content = manifest_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    data = load_toml(content)

    is_workspace = "workspace" in data
    workspace_data = data.get("workspace", {})

    if is_workspace:
        is_virtual = "package" not in data
        member_patterns = workspace_data.get("members", [])
        exclude_patterns = workspace_data.get("exclude", [])

        # Parse workspace.dependencies
        ws_deps_data = workspace_data.get("dependencies", {})
        ws_deps: Dict[str, Dependency] = {}
        if isinstance(ws_deps_data, dict):
            for name, spec in ws_deps_data.items():
                ws_deps[name] = parse_dependency(
                    name=name,
                    spec=spec,
                    section="workspace.dependencies",
                    manifest_path=manifest_path,
                    lines=lines,
                )

        ws_pkg = workspace_data.get("package", {})

        # Discover members
        member_manifests = discover_workspace_members(
            root_dir, member_patterns, exclude_patterns
        )

        members: List[Package] = []
        for m_path in member_manifests:
            try:
                pkg = parse_package(m_path)
                members.append(pkg)
            except Exception:
                # Still continue parsing remaining members if one has syntax issues
                pass

        # If not virtual, root manifest is also a member package
        if not is_virtual:
            root_pkg = parse_package(manifest_path)
            # Add root_pkg if not already in members
            if not any(m.manifest_path.resolve() == manifest_path.resolve() for m in members):
                members.insert(0, root_pkg)

        workspace = Workspace(
            root_path=root_dir,
            manifest_path=manifest_path,
            is_virtual=is_virtual,
            members=members,
            workspace_dependencies=ws_deps,
            workspace_package=ws_pkg,
            raw_data=data,
        )

        return Project(
            root_path=root_dir,
            is_workspace=True,
            workspace=workspace,
            packages=members,
            root_manifest=manifest_path,
        )
    else:
        # Check if parent directory is a workspace
        parent = root_dir.parent
        parent_manifest = parent / "Cargo.toml"
        if parent_manifest.is_file():
            try:
                parent_data = load_toml(parent_manifest)
                if "workspace" in parent_data:
                    # Can parse the full parent workspace
                    return parse_project(parent)
            except Exception:
                pass

        # Standalone single package
        pkg = parse_package(manifest_path)
        return Project(
            root_path=root_dir,
            is_workspace=False,
            workspace=None,
            packages=[pkg],
            root_manifest=manifest_path,
        )
