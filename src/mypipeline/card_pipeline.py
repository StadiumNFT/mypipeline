"""Implementation of the end-to-end card processing pipeline."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from .classifier import RuleBasedClassifier
from .clients import Gpt5VisionClient, load_rules
from .config import PipelineConfig
from .models import CardClassification, CardExtractionResult, CardScanPair

LOGGER = logging.getLogger(__name__)

_SIDE_ALIASES = {
    "front": {"front", "f", "obverse"},
    "back": {"back", "b", "reverse"},
}


class CardProcessingPipeline:
    """Coordinates pairing scans, invoking GPT-5, and classifying cards."""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        api_key = None
        organization = None
        if not config.dry_run:
            api_key = _read_env("OPENAI_API_KEY")
            organization = _read_env("OPENAI_ORG")
        self._client = Gpt5VisionClient(
            model=config.api_model,
            api_key=api_key,
            organization=organization,
            dry_run=config.dry_run,
        )
        classifier_rules = None
        if config.classification_rules_path:
            classifier_rules = load_rules(config.classification_rules_path)
        self._classifier = RuleBasedClassifier(classifier_rules)

    def discover_scan_files(self) -> List[Path]:
        allowed = {ext.lower() for ext in self.config.allowed_extensions}
        inbox = self.config.scans_inbox
        if not inbox.exists():
            LOGGER.warning("Scan inbox %s does not exist", inbox)
            return []
        files = [
            path
            for path in inbox.rglob("*")
            if path.is_file() and path.suffix.lower() in allowed
        ]
        files.sort()
        LOGGER.info("Discovered %d scan files in %s", len(files), inbox)
        return files

    def pair_scans(self, files: Sequence[Path]) -> List[CardScanPair]:
        groups: Dict[str, Dict[str, Path]] = {}
        for path in files:
            key, side = _derive_key_and_side(path)
            entry = groups.setdefault(key, {})
            if side in entry:
                LOGGER.warning("Duplicate %s scan detected for key %s", side, key)
            entry[side] = path
        pairs: List[CardScanPair] = []
        for key, entry in groups.items():
            front = entry.get("front")
            back = entry.get("back")
            if not front:
                LOGGER.warning("No front scan found for %s; skipping", key)
                continue
            pairs.append(CardScanPair(front_image=front, back_image=back))
        LOGGER.info("Constructed %d card pairs", len(pairs))
        return pairs

    def process_pairs(self, pairs: Iterable[CardScanPair]) -> List[CardExtractionResult]:
        results: List[CardExtractionResult] = []
        processed_dir = self.config.processed_output
        processed_dir.mkdir(parents=True, exist_ok=True)
        for pair in pairs:
            LOGGER.info("Processing card scans: %s", pair.front_image.name)
            result = self._client.analyze_pair(pair)
            classification = self._classify(result)
            if classification:
                result.classification = classification.label
                result.classification_details = classification
                details = asdict(classification)
            else:
                details = None
            payload = {
                "scan_pair": pair.as_payload(),
                "extraction": result.dict(),
                "classification_details": details,
            }
            results.append(result)
            self._write_card_payload(processed_dir, pair.front_image.stem, payload)
        self._write_results_summary(results)
        return results

    def _write_card_payload(self, directory: Path, stem: str, payload: Dict[str, object]) -> None:
        safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", stem)
        target = directory / f"{safe_stem}.json"
        target.write_text(json.dumps(payload, indent=2, default=str))

    def _write_results_summary(self, results: Sequence[CardExtractionResult]) -> None:
        summary_path = self.config.results_output
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary = [result.dict() for result in results]
        summary_path.write_text(json.dumps(summary, indent=2, default=str))
        LOGGER.info("Wrote summary for %d cards to %s", len(results), summary_path)

    def _classify(self, result: CardExtractionResult) -> CardClassification | None:
        try:
            return self._classifier.classify(result)
        except Exception:  # pragma: no cover - defensive logging
            LOGGER.exception("Classification failed")
            return None


def _derive_key_and_side(path: Path) -> tuple[str, str]:
    stem = path.stem
    lowered = stem.lower()
    for side, aliases in _SIDE_ALIASES.items():
        for alias in aliases:
            pattern = rf"(?:^|[-_\s]){alias}(?:$|[-_\s])"
            if re.search(pattern, lowered):
                base = re.sub(pattern, " ", lowered).strip()
                if not base:
                    base = stem.lower()
                return base, side
    return lowered, "front"


def _read_env(name: str) -> str | None:
    import os

    value = os.getenv(name)
    if value:
        LOGGER.debug("Using %s from environment", name)
    return value
