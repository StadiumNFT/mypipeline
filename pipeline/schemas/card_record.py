"""Pydantic schema for normalized card records."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from pydantic_core import PydanticUndefined


class Category(str, Enum):
    SPORTS = "sports"
    MARVEL = "marvel"
    POKEMON = "pokemon"
    OTHER = "other"


class Condition(str, Enum):
    NM = "NM"
    EX = "EX"
    VG = "VG"
    RAW = "raw-estimate"


CATEGORY_ALIASES = {
    "sport": Category.SPORTS,
    "sports": Category.SPORTS,
    "sports cards": Category.SPORTS,
    "trading card": Category.SPORTS,
    "marvel": Category.MARVEL,
    "comic": Category.MARVEL,
    "marvel card": Category.MARVEL,
    "pokemon": Category.POKEMON,
    "pokémon": Category.POKEMON,
    "tcg": Category.POKEMON,
    "other": Category.OTHER,
}

CONDITION_ALIASES = {
    "near mint": Condition.NM,
    "nm": Condition.NM,
    "mint": Condition.NM,
    "excellent": Condition.EX,
    "ex": Condition.EX,
    "very good": Condition.VG,
    "vg": Condition.VG,
    "raw": Condition.RAW,
    "raw estimate": Condition.RAW,
    "raw-estimate": Condition.RAW,
}

OPTIONAL_STR_FIELDS = (
    "brand",
    "set",
    "player",
    "character",
    "subset",
    "variant",
    "serial",
    "notes",
)


class CardRecord(BaseModel):
    sku: str
    cat: Category = Field(..., description="Category enum: sports, marvel, pokemon, other")
    brand: Optional[str] = None
    set: Optional[str] = None
    year: Optional[int] = None
    player: Optional[str] = None
    character: Optional[str] = None
    num: Optional[str] = None
    subset: Optional[str] = None
    variant: Optional[str] = None
    serial: Optional[str] = None
    auto: Optional[bool] = False
    mem: Optional[bool] = False
    grade: Optional[str] = "raw"
    cond: Optional[Condition] = None
    notes: Optional[str] = None
    price_est: Optional[float] = None
    conf: float

    model_config = ConfigDict(extra="ignore")

    @field_validator("sku", mode="before")
    @classmethod
    def trim_sku(cls, value: object) -> str:
        if isinstance(value, str):
            return value.strip()
        return str(value)

    @field_validator("cat", mode="before")
    @classmethod
    def validate_cat(cls, value: object) -> Category:
        if value is None or (isinstance(value, str) and not value.strip()):
            return Category.OTHER
        key = str(value).strip().lower()
        mapped = CATEGORY_ALIASES.get(key)
        if mapped:
            return mapped
        try:
            return Category(key)
        except ValueError:
            return Category.OTHER

    @field_validator("cond", mode="before")
    @classmethod
    def validate_cond(cls, value: object) -> Optional[Condition]:
        if value is None or value is PydanticUndefined:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        key = str(value).strip()
        alias = CONDITION_ALIASES.get(key.lower())
        if alias:
            return alias
        try:
            normalised = key.upper()
            return Condition(normalised)
        except ValueError:
            return None

    @field_validator("year", mode="before")
    @classmethod
    def coerce_year(cls, value: object) -> Optional[int]:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @field_validator("grade", mode="before")
    @classmethod
    def default_grade(cls, value: object) -> str:
        if value in (None, "") or value is PydanticUndefined:
            return "raw"
        return str(value).strip() or "raw"

    @field_validator("player", "character", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> Optional[str]:
        if value is None or value is PydanticUndefined:
            return None
        if isinstance(value, str):
            text = value.strip()
            return text or None
        return str(value)

    @field_validator("num", mode="before")
    @classmethod
    def str_number(cls, value: object) -> Optional[str]:
        if value is None or value is PydanticUndefined:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("price_est", mode="before")
    @classmethod
    def to_float(cls, value: object) -> Optional[float]:
        if value in (None, "") or value is PydanticUndefined:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @field_validator("auto", "mem", mode="before")
    @classmethod
    def to_bool(cls, value: object) -> Optional[bool]:
        if value in (None, "") or value is PydanticUndefined:
            return False
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        return text in {"1", "true", "yes", "y"}

    @field_validator("conf", mode="before")
    @classmethod
    def to_conf(cls, value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @field_validator(*OPTIONAL_STR_FIELDS, mode="before")
    @classmethod
    def empty_to_none(cls, value: object) -> Optional[str]:
        if value is None or value is PydanticUndefined:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value)

    @model_validator(mode="after")
    def enforce_identity(self) -> "CardRecord":
        if self.player and self.character:
            if self.cat == Category.SPORTS:
                self.character = None
            else:
                self.player = None
        return self
