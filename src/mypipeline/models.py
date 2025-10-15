"""Data models used across the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(slots=True)
class CardScanPair:
    """Represents a pair of front and back scan images for a single card."""

    front_image: Path
    back_image: Optional[Path] = None
    metadata: Optional[Dict[str, str]] = None

    def as_payload(self) -> Dict[str, Optional[str]]:
        return {
            "front_image": str(self.front_image),
            "back_image": str(self.back_image) if self.back_image else None,
            "metadata": self.metadata or {},
        }


@dataclass(slots=True)
class CardExtractionResult:
    """Structured information returned by the GPT-5 vision endpoint."""

    raw_response: Dict[str, object]
    card_name: str
    set_name: Optional[str]
    card_number: Optional[str]
    condition: Optional[str]
    attributes: Dict[str, object]
    classification: Optional[str] = None
    classification_details: Optional[CardClassification] = None

    def dict(self) -> Dict[str, object]:
        return {
            "card_name": self.card_name,
            "set_name": self.set_name,
            "card_number": self.card_number,
            "condition": self.condition,
            "attributes": self.attributes,
            "classification": self.classification,
            "classification_details": self.classification_details.dict()
            if self.classification_details
            else None,
            "raw_response": self.raw_response,
        }


@dataclass(slots=True)
class CardClassification:
    """Describes a classification outcome for a card."""

    label: str
    confidence: float
    reasons: List[str]

    def dict(self) -> Dict[str, object]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "reasons": self.reasons,
        }
