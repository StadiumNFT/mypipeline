"""Rule-based classification for extracted card data."""

from __future__ import annotations

import operator
from typing import Dict, Iterable, List, Optional

from .models import CardClassification, CardExtractionResult


class RuleBasedClassifier:
    """Evaluate a set of rules against GPT extraction results."""

    def __init__(self, rules: Optional[Dict[str, object]] = None) -> None:
        self._rules = self._normalise_rules(rules or {})

    def classify(self, result: CardExtractionResult) -> Optional[CardClassification]:
        for rule in self._rules:
            if self._evaluate_rule(rule["criteria"], result):
                return CardClassification(
                    label=rule["label"],
                    confidence=rule.get("confidence", 0.5),
                    reasons=rule.get("reasons", []),
                )
        return None

    @staticmethod
    def _normalise_rules(rules: Dict[str, object]) -> List[Dict[str, object]]:
        if "rules" in rules:
            entries = rules["rules"]
        else:
            entries = rules
        if isinstance(entries, dict):
            entries = list(entries.values())
        if not isinstance(entries, list):
            raise ValueError("Rules configuration must be a list or mapping of rules")
        normalised = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Each rule must be a dictionary")
            if "label" not in entry or "criteria" not in entry:
                raise ValueError("Rule requires 'label' and 'criteria'")
            criteria = entry["criteria"]
            if not isinstance(criteria, list) or not criteria:
                raise ValueError("Rule criteria must be a non-empty list")
            normalised.append(entry)
        return normalised

    @staticmethod
    def _evaluate_rule(criteria: Iterable[Dict[str, object]], result: CardExtractionResult) -> bool:
        for check in criteria:
            field = check.get("field")
            if not field:
                return False
            value = RuleBasedClassifier._resolve_field(field, result)
            if "equals" in check and value != check["equals"]:
                return False
            if "contains" in check:
                expected = check["contains"]
                if isinstance(expected, str):
                    expected = [expected]
                if not any(str(val).lower() in str(value).lower() for val in expected):
                    return False
            if "in" in check:
                expected = check["in"]
                if value not in expected:
                    return False
            if "greater_than" in check:
                if RuleBasedClassifier._compare(value, check["greater_than"], operator.le):
                    return False
            if "less_than" in check:
                if RuleBasedClassifier._compare(value, check["less_than"], operator.ge):
                    return False
        return True

    @staticmethod
    def _resolve_field(field: str, result: CardExtractionResult):
        value = result.dict()
        for segment in field.split("."):
            if isinstance(value, dict) and segment in value:
                value = value[segment]
            else:
                return None
        return value

    @staticmethod
    def _compare(value, other, comparator):
        try:
            return comparator(float(value), float(other))
        except (TypeError, ValueError):
            return False
