"""Configuration utilities for the card processing pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, Field, validator


class PipelineConfig(BaseModel):
    """Runtime configuration for the pipeline."""

    scans_inbox: Path = Field(
        default_factory=lambda: Path.cwd() / "scans" / "Scans_Inbox",
        description="Directory containing raw scan image files.",
    )
    processed_output: Path = Field(
        default_factory=lambda: Path.cwd() / "scans" / "Processed",
        description="Directory where processed payloads and artefacts will be written.",
    )
    results_output: Path = Field(
        default_factory=lambda: Path.cwd() / "scans" / "results.json",
        description="Path to the JSON file that stores card extraction results.",
    )
    allowed_extensions: Iterable[str] = Field(
        default=(".jpg", ".jpeg", ".png", ".tif", ".tiff"),
        description="Image file extensions that should be considered when pairing scans.",
    )
    dry_run: bool = Field(
        default=False,
        description="If True, the GPT client will not be invoked and sample payloads are returned instead.",
    )
    max_parallel_requests: int = Field(
        default=2,
        ge=1,
        description="Maximum number of concurrent GPT requests to issue when processing cards.",
    )
    api_model: str = Field(
        default="gpt-5.0-vision-preview",
        description="Model identifier for the GPT-5 vision endpoint.",
    )
    classification_rules_path: Optional[Path] = Field(
        default=None,
        description="Optional path to a JSON or YAML file defining card classification rules.",
    )

    class Config:
        arbitrary_types_allowed = True

    @validator("scans_inbox", "processed_output", "results_output", pre=True)
    def _expand_path(cls, value: Path | str) -> Path:
        return Path(value).expanduser().resolve()
