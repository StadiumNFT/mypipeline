"""Utilities for building prompt hints and few-shot exemplars."""
from __future__ import annotations

import json
import os
import random
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from . import naming

PROMPTS_DIR = Path("pipeline/prompts")
RULES_PATH = PROMPTS_DIR / "rules_minimal.txt"
EXEMPLARS_DIR = PROMPTS_DIR / "exemplars"
CACHE_DIR = Path("pipeline/cache")
HINTS_DB = CACHE_DIR / "hints.sqlite"
DEFAULT_IMAGE_EDGE = 1024


def load_rules() -> str:
    if RULES_PATH.exists():
        return RULES_PATH.read_text(encoding="utf-8").strip()
    # Fallback to a short block if the file is missing.
    return (
        "You are a card cataloger. Return only JSON using keys: sku, cat, brand, set, year, "
        "player or character, num, subset, variant, serial, auto, mem, grade, cond, notes, "
        "price_est, conf. Use images first; hints second. Populate only what’s present. If "
        "uncertain, set conf < 0.7 and say why in notes. Prefer canonical set names. Detect "
        "autograph/memorabilia/serial from visuals. For sports use 'player'; for non-sports "
        "use 'character'. Keep strings short. Output exactly one JSON object."
    )


def _read_env_defaults(root: Path) -> Dict[str, str]:
    env_path = root / ".env"
    if not env_path.exists():
        return {}
    values: Dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def determine_capsule(sku: str, project_root: Path | None = None) -> Dict[str, Any]:
    base = naming.parse_sku(sku)
    batch = base["batch_code"]
    likely_cat = {
        "MM": "marvel",
        "DG": "marvel",
        "BD": "marvel",
        "SP": "sports",
        "FB": "sports",
        "BB": "sports",
        "PK": "pokemon",
    }.get(batch, "other")

    capsule: Dict[str, Any] = {
        "sku": sku,
        "likely_cat": likely_cat,
        "likely_year_range": "2015-2022",
        "canonical_set_candidates": ["Fleer Ultra", "Upper Deck Marvel", "Topps Chrome"],
        "brand_candidates": ["Upper Deck", "Topps"],
        "subset_vocab": ["Base", "Holo", "PMG", "Canvas"],
        "number_format_hint": "### or ###a",
        "common_ocr_fixes": {
            "O-Pee-Chee": "O-Pee-Chee",
            "Fleer Ultra": "Fleer Ultra",
        },
        "banned_words": ["collectible trading card", "vibrant"],
        "known_parallels": ["PMG", "Spectrum", "Canvas"],
        "backside_tells": ["Short Print", "Checklist"],
    }

    if project_root:
        env_values = _read_env_defaults(project_root)
        if "IMAGE_MAX_EDGE" in env_values:
            capsule["image_max_edge"] = int(env_values["IMAGE_MAX_EDGE"])
    if HINTS_DB.exists():
        capsule["has_cache"] = True
    return capsule


@lru_cache()
def _load_exemplar_bank() -> List[Dict[str, Any]]:
    exemplars: List[Dict[str, Any]] = []
    if not EXEMPLARS_DIR.exists():
        return exemplars
    for path in EXEMPLARS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            exemplars.extend(data)
    return exemplars


def select_exemplars(capsule: Dict[str, Any], limit: int = 2) -> List[Dict[str, Any]]:
    bank = _load_exemplar_bank()
    if not bank:
        return []
    cat = capsule.get("likely_cat")
    matches = [ex for ex in bank if cat and cat in ex.get("tags", [])]
    if not matches:
        matches = [ex for ex in bank if "general" in ex.get("tags", [])]
    random.shuffle(matches)
    return matches[:limit]


def build_hint_payload(sku: str, project_root: Path | None = None) -> Dict[str, Any]:
    capsule = determine_capsule(sku, project_root=project_root)
    exemplars = select_exemplars(capsule)
    return {
        "sku": sku,
        "capsule": capsule,
        "exemplars": exemplars,
        "rules": load_rules(),
    }
