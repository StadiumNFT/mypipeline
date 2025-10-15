"""Pydantic schema for normalized card records."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, validator

VALID_CATEGORIES = {"sports", "marvel", "pokemon", "other"}
VALID_COND = {"NM", "EX", "VG", "raw-estimate"}


class CardRecord(BaseModel):
    sku: str
    cat: str = Field(..., description="Category enum: sports, marvel, pokemon, other")
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
    cond: Optional[str] = None
    notes: Optional[str] = None
    price_est: Optional[float] = None
    conf: float

    class Config:
        extra = "ignore"

    @validator("cat")
    def validate_cat(cls, value: str) -> str:
        if value:
            value = value.lower()
        if value not in VALID_CATEGORIES:
            return "other"
        return value

    @validator("cond")
    def validate_cond(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.upper()
        if value.lower() == "raw":
            return "raw-estimate"
        if value not in VALID_COND:
            return None
        return value

    @validator("year", pre=True)
    def coerce_year(cls, value):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @validator("grade", pre=True, always=True)
    def default_grade(cls, value):
        if not value:
            return "raw"
        return value

    @validator("player", "character", pre=True)
    def strip_text(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @validator("num", pre=True)
    def str_number(cls, value):
        if value is None:
            return None
        return str(value).strip()
