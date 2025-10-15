"""GPT-5 vision client abstraction."""

from __future__ import annotations

import json
import logging
from base64 import b64encode
from pathlib import Path
from typing import Dict, Iterable, Optional

from openai import OpenAI

from .models import CardExtractionResult, CardScanPair

LOGGER = logging.getLogger(__name__)


class Gpt5VisionClient:
    """Wrapper around the OpenAI GPT-5 API for multimodal analysis."""

    def __init__(
        self,
        model: str,
        *,
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        dry_run: bool = False,
    ) -> None:
        self._model = model
        self._dry_run = dry_run
        if dry_run:
            self._client = None
        else:
            kwargs = {}
            if api_key:
                kwargs["api_key"] = api_key
            if organization:
                kwargs["organization"] = organization
            self._client = OpenAI(**kwargs)

    def analyze_pair(self, pair: CardScanPair) -> CardExtractionResult:
        """Send the card pair to the GPT-5 API and return structured data."""

        if self._dry_run:
            LOGGER.info("Dry-run enabled; returning synthetic response for %s", pair.front_image)
            return self._mock_response(pair)

        assert self._client is not None, "Client should be initialized when dry_run is False"
        LOGGER.debug("Sending payload for %s", pair.front_image)
        with pair.front_image.open("rb") as front_fp:
            front_bytes = b64encode(front_fp.read()).decode("ascii")
        back_bytes = None
        if pair.back_image:
            with pair.back_image.open("rb") as back_fp:
                back_bytes = b64encode(back_fp.read()).decode("ascii")

        contents: Iterable[Dict[str, object]] = [
            {
                "role": "system",
                "content": "You are an expert sports trading card grader. Extract structured data in JSON.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Identify the card shown in the scans and return structured JSON matching the provided schema.",
                    },
                    {
                        "type": "input_image",
                        "image_base64": front_bytes,
                    },
                ],
            },
        ]
        if back_bytes:
            contents[1]["content"].append({"type": "input_image", "image_base64": back_bytes})

        response = self._client.responses.create(
            model=self._model,
            input=list(contents),
            max_output_tokens=800,
            response_format={
                "type": "json_schema",
                "json_schema": self._schema(),
            },
        )
        LOGGER.debug("Received response: %s", response)
        parsed_payload = json.loads(response.output[0].content[0].text)
        return self._to_result(parsed_payload)

    @staticmethod
    def _mock_response(pair: CardScanPair) -> CardExtractionResult:
        raw_payload = {
            "card_name": "Demo Card",
            "set_name": "Sample Set",
            "card_number": "123",
            "condition": "Near Mint",
            "attributes": {
                "front_image": pair.front_image.name,
                "back_image": pair.back_image.name if pair.back_image else None,
            },
        }
        return Gpt5VisionClient._to_result(raw_payload)

    @staticmethod
    def _to_result(payload: Dict[str, object]) -> CardExtractionResult:
        return CardExtractionResult(
            raw_response=payload,
            card_name=str(payload.get("card_name", "Unknown")),
            set_name=payload.get("set_name"),
            card_number=payload.get("card_number"),
            condition=payload.get("condition"),
            attributes=payload.get("attributes", {}),
        )

    @staticmethod
    def _schema() -> Dict[str, object]:
        return {
            "name": "card_extraction_schema",
            "strict": False,
            "schema": {
                "type": "object",
                "properties": {
                    "card_name": {"type": "string"},
                    "set_name": {"type": ["string", "null"]},
                    "card_number": {"type": ["string", "null"]},
                    "condition": {"type": ["string", "null"]},
                    "attributes": {"type": "object"},
                },
                "required": ["card_name", "attributes"],
                "additionalProperties": True,
            },
        }


def load_rules(path: Path) -> Dict[str, object]:
    """Load classification rules from JSON or YAML."""

    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text()
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "PyYAML must be installed to load YAML classification rules"
            ) from exc
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Classification rules file must define a JSON object")
    return data
