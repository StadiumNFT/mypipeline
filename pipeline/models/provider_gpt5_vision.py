"""Adapter for calling the GPT-5 Vision model with strict JSON output."""
from __future__ import annotations

import base64
import json
import logging
import os
import random
import time
from typing import Any, Dict, List

from openai import OpenAI

try:  # pragma: no cover - optional exception imports
    from openai import APIStatusError, RateLimitError
except ImportError:  # pragma: no cover - fallback for older SDKs
    APIStatusError = RateLimitError = Exception  # type: ignore

try:  # pragma: no cover - optional exception imports
    from openai import APITimeoutError
except ImportError:  # pragma: no cover - fallback for older SDKs
    APITimeoutError = Exception  # type: ignore

DEFAULT_MODEL_NAME = "gpt-5.1-vision"
DEFAULT_TIMEOUT = 45
MAX_ATTEMPTS = 4
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}
TELEMETRY_SAMPLE_RATE = int(os.getenv("PIPELINE_TELEMETRY_SAMPLE", "20") or 20)

LOGGER = logging.getLogger(__name__)


class MissingAPIKey(RuntimeError):
    """Raised when the AG5 API key cannot be located."""


def _load_rules_text(hints: Dict[str, Any]) -> str:
    rules = hints.get("rules")
    if isinstance(rules, str) and rules.strip():
        return rules.strip()
    rules_path = hints.get("rules_path")
    if rules_path and os.path.exists(rules_path):
        with open(rules_path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    # Last resort minimal rules.
    return (
        "You are a card cataloger. Return only JSON using the agreed keys."
    )


def _encode_image(path: str) -> Dict[str, Any]:
    with open(path, "rb") as handle:
        payload = base64.b64encode(handle.read()).decode("utf-8")
    return {
        "type": "input_image",
        "image_url": {
            "url": f"data:image/webp;base64,{payload}"
        },
    }


def _summarise_example(example: Dict[str, Any]) -> str:
    body = {
        "input": example.get("input", ""),
        "output": example.get("output", {}),
    }
    return json.dumps(body, separators=(",", ":"))


def analyze_card(front_path: str, back_path: str, hints: Dict[str, Any]) -> Dict[str, Any]:
    """Run the GPT-5 Vision model and return a JSON dictionary.

    Parameters
    ----------
    front_path: str
        Path to the prepared (compressed) front image.
    back_path: str
        Path to the prepared (compressed) back image.
    hints: Dict[str, Any]
        Metadata required to assemble the prompt. Expected keys include:
        - sku: card identifier
        - capsule: small hints dictionary
        - exemplars: list of exemplar dicts (optional)
        - rules: optional override rules text
        - rules_path: fallback path to rules file
        - token_limit: optional maximum output token budget
        - model_name: override model name
        - nudge: optional retry nudge string

    Returns
    -------
    Dict[str, Any]
        Parsed JSON response from the model.
    """

    api_key = os.getenv("AG5_API_KEY")
    if not api_key:
        raise MissingAPIKey(
            "AG5_API_KEY is not set. Populate it in your .env or environment."
        )

    client = OpenAI(api_key=api_key)
    model_name = hints.get("model_name") or os.getenv("MODEL_NAME") or DEFAULT_MODEL_NAME
    max_tokens = int(hints.get("token_limit") or os.getenv("TOKEN_LIMIT") or 900)
    timeout = int(hints.get("timeout") or os.getenv("PIPELINE_REQUEST_TIMEOUT", DEFAULT_TIMEOUT))

    capsule = hints.get("capsule") or {}
    capsule_text = json.dumps(capsule, ensure_ascii=False, separators=(",", ":"))
    exemplars: List[Dict[str, Any]] = hints.get("exemplars") or []
    sku = hints.get("sku", "")
    rules_text = _load_rules_text(hints)

    user_content: List[Dict[str, Any]] = []
    user_content.append({"type": "text", "text": f"Hints: {capsule_text}"})
    if exemplars:
        user_content.append({"type": "text", "text": "Few-shot:"})
        for example in exemplars[:2]:
            user_content.append({"type": "text", "text": _summarise_example(example)})
    nudge = hints.get("nudge")
    if nudge:
        user_content.append({"type": "text", "text": f"Nudge: {nudge}"})
    user_content.append(
        {
            "type": "text",
            "text": f"Images: front={os.path.basename(front_path)}, back={os.path.basename(back_path)}; sku={sku}",
        }
    )
    user_content.append(_encode_image(front_path))
    user_content.append(_encode_image(back_path))

    if TELEMETRY_SAMPLE_RATE > 0 and random.randint(1, TELEMETRY_SAMPLE_RATE) == 1:
        LOGGER.info(
            "gpt5_request sku=%s exemplars=%d hints_chars=%d",
            sku,
            len(exemplars),
            len(capsule_text),
        )

    def _send_request() -> Dict[str, Any]:
        response = client.responses.create(
            model=model_name,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": rules_text,
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            temperature=0.1,
            max_output_tokens=max_tokens,
            timeout=timeout,
        )
        return response

    delay = 1.0
    attempts = 0
    last_exc: Exception | None = None
    response = None
    while attempts < MAX_ATTEMPTS:
        attempts += 1
        try:
            response = _send_request()
            break
        except (RateLimitError, APITimeoutError) as exc:
            last_exc = exc
        except APIStatusError as exc:  # pragma: no cover - network branch
            last_exc = exc
            status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
            if status not in RETRYABLE_STATUS:
                raise
        except Exception:
            raise
        if attempts >= MAX_ATTEMPTS:
            assert last_exc is not None
            raise last_exc
        time.sleep(delay)
        delay = min(delay * 2, 8.0)

    if response is None:  # pragma: no cover - safety net
        raise RuntimeError("Failed to receive response from GPT-5 Vision")

    # Collect the first text block returned.
    text_chunks: List[str] = []
    for item in response.output or []:
        for piece in item.get("content", []):
            if piece.get("type") == "output_text":
                text_chunks.append(piece.get("text", ""))
    if not text_chunks:
        raise RuntimeError("Model did not return any text content.")
    raw = "\n".join(text_chunks).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model response was not valid JSON: {raw}") from exc
