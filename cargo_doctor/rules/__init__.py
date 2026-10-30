"""Registry and exports for cargo-doctor rules."""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from cargo_doctor.rules.base import BaseRule
from cargo_doctor.rules.duplicate_deps import (
    DuplicateDependencyRule,
    WorkspaceInheritanceMismatchRule,
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

ALL_RULES: List[Type[BaseRule]] = [
    DuplicateDependencyRule,
    WorkspaceInheritanceMismatchRule,
    WildcardDependencyRule,
    UnpinnedGitDependencyRule,
    OpenEndedRangeRule,
    OutdatedEditionRule,
    MissingEditionRule,
    MissingDescriptionRule,
    MissingLicenseRule,
    MissingRepositoryRule,
    MissingReadmeRule,
    MissingMSRVRule,
    WorkspaceInheritanceRecommendationRule,
]

RULES_BY_ID: Dict[str, Type[BaseRule]] = {rule_cls.id: rule_cls for rule_cls in ALL_RULES}
RULES_BY_NAME: Dict[str, Type[BaseRule]] = {rule_cls.name: rule_cls for rule_cls in ALL_RULES}


def get_rules(
    include_ids_or_names: Optional[List[str]] = None,
    exclude_ids_or_names: Optional[List[str]] = None,
) -> List[BaseRule]:
    """Instantiate and filter rules according to include and exclude criteria."""
    include_set = set(include_ids_or_names) if include_ids_or_names else None
    exclude_set = set(exclude_ids_or_names) if exclude_ids_or_names else set()

    selected_rules: List[BaseRule] = []

    for rule_cls in ALL_RULES:
        rule_id = rule_cls.id
        rule_name = rule_cls.name

        # Check exclusion
        if rule_id in exclude_set or rule_name in exclude_set:
            continue

        # Check inclusion
        if include_set is not None:
            if rule_id not in include_set and rule_name not in include_set:
                continue

        selected_rules.append(rule_cls())

    return selected_rules
