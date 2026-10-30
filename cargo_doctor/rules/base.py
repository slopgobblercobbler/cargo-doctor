"""Base rule interface for cargo-doctor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from cargo_doctor.models import Issue, Project, Severity


class BaseRule(ABC):
    """Abstract base class for all inspection rules."""

    id: str = ""
    name: str = ""
    description: str = ""
    default_severity: Severity = Severity.WARNING
    fixable: bool = False

    @abstractmethod
    def check(self, project: Project) -> List[Issue]:
        """Inspect the project and return a list of detected issues."""
        raise NotImplementedError
