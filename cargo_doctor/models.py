"""Data models for cargo-doctor."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class Severity(str, Enum):
    """Issue severity levels."""

    ERROR = "error"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    INFO = "info"

    @property
    def color(self) -> str:
        """Terminal color for severity."""
        if self == Severity.ERROR:
            return "red"
        if self == Severity.WARNING:
            return "yellow"
        if self == Severity.SUGGESTION:
            return "cyan"
        return "blue"

    @property
    def badge(self) -> str:
        """Text badge for severity."""
        if self == Severity.ERROR:
            return "[ERROR]"
        if self == Severity.WARNING:
            return "[WARN]"
        if self == Severity.SUGGESTION:
            return "[SUGG]"
        return "[INFO]"


@dataclass
class Dependency:
    """Represents a Rust crate dependency declaration."""

    name: str
    spec: Union[str, Dict[str, Any]]
    version: Optional[str] = None
    path: Optional[str] = None
    git: Optional[str] = None
    branch: Optional[str] = None
    tag: Optional[str] = None
    rev: Optional[str] = None
    workspace: bool = False
    features: List[str] = field(default_factory=list)
    optional: bool = False
    default_features: Optional[bool] = None
    section: str = "dependencies"  # dependencies, dev-dependencies, build-dependencies
    target: Optional[str] = None
    manifest_path: Optional[Path] = None
    line_number: Optional[int] = None

    @property
    def is_workspace_inherited(self) -> bool:
        """Whether this dependency inherits from workspace."""
        return self.workspace

    @property
    def is_wildcard(self) -> bool:
        """Whether version is wildcard *."""
        if self.version is None:
            return False
        return self.version.strip() == "*" or self.version.strip() == "^*"

    @property
    def is_unpinned_git(self) -> bool:
        """Whether git dependency lacks an immutable rev or tag."""
        if not self.git:
            return False
        # If git is set, it should have rev or tag (branch is mutable!)
        return not bool(self.rev or self.tag)


@dataclass
class Package:
    """Represents a Rust package defined in Cargo.toml."""

    name: str
    version: str
    manifest_path: Path
    edition: Optional[str] = None
    description: Optional[str] = None
    license: Optional[str] = None
    license_file: Optional[str] = None
    repository: Optional[str] = None
    homepage: Optional[str] = None
    readme: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    authors: List[str] = field(default_factory=list)
    rust_version: Optional[str] = None
    publish: Union[bool, List[str]] = True
    dependencies: List[Dependency] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_publishable(self) -> bool:
        """Whether this package is intended to be published to crates.io."""
        if self.publish is False:
            return False
        if isinstance(self.publish, list) and len(self.publish) == 0:
            return False
        return True

    @property
    def dependencies_by_name(self) -> Dict[str, List[Dependency]]:
        """Group dependencies by crate name."""
        result: Dict[str, List[Dependency]] = {}
        for dep in self.dependencies:
            result.setdefault(dep.name, []).append(dep)
        return result


@dataclass
class Workspace:
    """Represents a Cargo workspace."""

    root_path: Path
    manifest_path: Path
    is_virtual: bool
    members: List[Package] = field(default_factory=list)
    workspace_dependencies: Dict[str, Dependency] = field(default_factory=dict)
    workspace_package: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Project:
    """Represents a Cargo project (single crate or workspace)."""

    root_path: Path
    is_workspace: bool
    workspace: Optional[Workspace] = None
    packages: List[Package] = field(default_factory=list)
    root_manifest: Optional[Path] = None

    @property
    def all_packages(self) -> List[Package]:
        """All packages in project."""
        if self.is_workspace and self.workspace:
            return self.workspace.members
        return self.packages


@dataclass
class Issue:
    """Represents a detected issue or recommendation in Cargo.toml."""

    rule_id: str
    rule_name: str
    severity: Severity
    message: str
    file_path: Path
    line_number: Optional[int] = None
    fixable: bool = False
    suggestion: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to JSON-serializable dictionary."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "file_path": str(self.file_path),
            "line_number": self.line_number,
            "fixable": self.fixable,
            "suggestion": self.suggestion,
            "context": self.context,
        }


@dataclass
class ScanResult:
    """Represents overall project health scan result."""

    project_path: Path
    is_workspace: bool
    packages_count: int
    total_dependencies_count: int
    unique_dependencies_count: int
    health_score: int  # 0 to 100
    grade: str  # A, B, C, D, F
    issues: List[Issue] = field(default_factory=list)
    editions: Dict[str, int] = field(default_factory=dict)

    @property
    def errors_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warnings_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def suggestions_count(self) -> int:
        return sum(1 for i in self.issues if i.severity in (Severity.SUGGESTION, Severity.INFO))

    @property
    def fixable_count(self) -> int:
        return sum(1 for i in self.issues if i.fixable)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_path": str(self.project_path),
            "is_workspace": self.is_workspace,
            "packages_count": self.packages_count,
            "total_dependencies_count": self.total_dependencies_count,
            "unique_dependencies_count": self.unique_dependencies_count,
            "health_score": self.health_score,
            "grade": self.grade,
            "summary": {
                "errors": self.errors_count,
                "warnings": self.warnings_count,
                "suggestions": self.suggestions_count,
                "fixable": self.fixable_count,
            },
            "editions": self.editions,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass
class FixResult:
    """Represents the outcome of an automated fix operation."""

    files_modified: List[Path] = field(default_factory=list)
    diffs: Dict[Path, str] = field(default_factory=dict)
    fixed_issues_count: int = 0
    dry_run: bool = False
    details: List[str] = field(default_factory=list)
