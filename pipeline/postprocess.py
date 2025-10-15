import csv
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image

from pipeline.models.provider_gpt5_vision import analyze_card as run_gpt5
from pipeline.models.provider_gpt5_vision import MissingAPIKey
from pipeline.schemas.card_record import CardRecord
from pipeline.utils import log, naming
from pipeline.utils.hints import build_hint_payload
from pydantic import ValidationError

RESULT_SUBDIR = "results"
DEFAULT_CONFIG = {
    "provider": "Mock",
    "model_name": "gpt-5.1-vision",
    "max_tokens": 900,
    "compress_images": True,
    "image_max_edge": 1024,
}
CONFIG_PATH = Path("pipeline/config/model.json")
RULES_PATH = Path("pipeline/prompts/rules_minimal.txt")
TMP_DIR = Path("pipeline/tmp")


def _load_env(project_root: Path) -> None:
    env_path = project_root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return dict(DEFAULT_CONFIG)
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    return merged


def _find_front_back(folder: Path, images: List[str]) -> Tuple[Path, Path]:
    front = None
    back = None
    for name in images:
        lower = name.lower()
        path = folder / name
        if "_f" in lower or "front" in lower:
            front = path
        elif "_b" in lower or "back" in lower:
            back = path
    if front is None and images:
        front = folder / images[0]
    if back is None:
        if front is not None and len(images) > 1:
            candidates = [folder / name for name in images if (folder / name) != front]
            back = candidates[0] if candidates else front
        else:
            back = front
    if front is None or back is None:
        raise FileNotFoundError(f"Could not resolve front/back images in {folder}")
    return front, back


def _compress_image(src: Path, dest: Path, max_edge: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        img = img.convert("RGB") if img.mode in {"P", "RGBA"} else img
        width, height = img.size
        scale = max(width, height)
        if scale > max_edge:
            ratio = max_edge / float(scale)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        img.save(dest, format="WEBP", quality=85)


def _prepare_images(front: Path, back: Path, sku: str, job_id: str, compress: bool, max_edge: int) -> Tuple[Path, Path]:
    if not compress:
        return front, back
    job_tmp = TMP_DIR / job_id / sku
    front_out = job_tmp / f"{front.stem}.webp"
    back_out = job_tmp / f"{back.stem}.webp"
    _compress_image(front, front_out, max_edge)
    _compress_image(back, back_out, max_edge)
    return front_out, back_out


def _fake_model_response(sku: str, capsule: Dict[str, Any]) -> Dict[str, Any]:
    base = naming.parse_sku(sku)
    guess_cat = capsule.get("likely_cat") or "other"
    identity_key = "player" if guess_cat == "sports" else "character"
    response = {
        "sku": sku,
        "cat": guess_cat,
        "brand": "Ageless",
        "set": "Prototype",
        "year": 2025,
        "num": str(base["seq"]),
        "subset": "Base",
        "variant": "",
        "serial": "",
        "auto": False,
        "mem": False,
        "grade": "raw",
        "cond": "raw-estimate",
        "notes": "Mock response",
        "price_est": 0.0,
        "conf": 0.62,
    }
    response[identity_key] = "TBD"
    return response


def _needs_retry(record: Dict[str, Any]) -> bool:
    required_missing = any(not record.get(field) for field in ("year", "set", "num"))
    return record.get("conf", 0.0) < 0.65 or required_missing


def _build_nudge(record: Dict[str, Any], capsule: Dict[str, Any]) -> str:
    missing_fields = [field for field in ("year", "set", "num") if not record.get(field)]
    notes = []
    if missing_fields:
        notes.append(f"Fill {', '.join(missing_fields)} if visible")
    subset_vocab = capsule.get("subset_vocab") or []
    if subset_vocab:
        notes.append(f"Subset options: {', '.join(subset_vocab[:4])}")
    return ", ".join(notes) or "Double-check visible text on the back."


def _normalise(raw: Dict[str, Any]) -> Dict[str, Any]:
    card = CardRecord(**raw)
    data = card.model_dump(exclude_none=True)
    # Enforce single identity field
    if data.get("player") and data.get("character"):
        data.pop("character")
    if "price_est" in data and data["price_est"] == 0:
        data.pop("price_est")
    return data


def _write_outputs(out_root: Path, sku: str, record: Dict[str, Any], needs_review: bool) -> None:
    json_dir = out_root / "json"
    txt_dir = out_root / "txt"
    csv_dir = out_root / "csv"
    for directory in (json_dir, txt_dir, csv_dir):
        directory.mkdir(parents=True, exist_ok=True)

    with (json_dir / f"{sku}.json").open("w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)

    identity = record.get("player") or record.get("character") or ""
    headline = f"{record.get('year', '????')} {record.get('set', 'Unknown set')} #{record.get('num', '?')} {identity}".strip()
    status = "Needs review" if needs_review else f"conf {record.get('conf', 0):.2f}"
    lines = [headline, f"Category={record.get('cat')}, {status}"]
    if record.get("notes"):
        lines.append(record["notes"])
    with (txt_dir / f"{sku}.txt").open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    csv_path = csv_dir / "batch.csv"
    row = {
        "sku": record.get("sku"),
        "cat": record.get("cat"),
        "brand": record.get("brand"),
        "set": record.get("set"),
        "year": record.get("year"),
        "identity": identity,
        "num": record.get("num"),
        "subset": record.get("subset"),
        "variant": record.get("variant"),
        "serial": record.get("serial"),
        "auto": record.get("auto"),
        "mem": record.get("mem"),
        "grade": record.get("grade"),
        "cond": record.get("cond"),
        "notes": record.get("notes"),
        "price_est": record.get("price_est"),
        "conf": record.get("conf"),
        "needs_review": needs_review,
    }
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def _summarise(record: Dict[str, Any], needs_review: bool) -> str:
    name = record.get("player") or record.get("character") or ""
    set_name = record.get("set", "?")
    year = record.get("year", "?")
    conf = record.get("conf", 0.0)
    flag = " ⚠️" if needs_review else ""
    return f"{year} {set_name} {record.get('num', '?')} {name} :: conf={conf:.2f}{flag}"


def process_batch(job_id: str, ready: str = "Scans_Ready", batches: str = "pipeline/output/batches", outroot: str = "pipeline/output") -> str:
    project_root = Path.cwd()
    _load_env(project_root)
    config = _load_config()

    batch_file = Path(batches) / f"{job_id}.jsonl"
    if not batch_file.exists():
        raise FileNotFoundError(batch_file)

    result_root = Path(outroot) / job_id / RESULT_SUBDIR
    if result_root.exists():
        shutil.rmtree(result_root)

    TMP_DIR.mkdir(parents=True, exist_ok=True)

    with batch_file.open("r", encoding="utf-8") as handle:
        lines = [json.loads(line) for line in handle if line.strip()]

    for item in lines:
        sku = item["sku"]
        folder = Path(ready) / sku
        images = item.get("images", [])
        front_path, back_path = _find_front_back(folder, images)
        front_prepped, back_prepped = _prepare_images(
            front_path,
            back_path,
            sku,
            job_id,
            config.get("compress_images", True),
            int(config.get("image_max_edge", 1024)),
        )

        hint_payload = build_hint_payload(sku, project_root=project_root)
        response_data: Dict[str, Any]

        if config.get("provider") == "GPT-5 Vision":
            hint_payload.update(
                {
                    "rules_path": str(RULES_PATH),
                    "model_name": config.get("model_name"),
                    "token_limit": config.get("max_tokens"),
                }
            )
            try:
                response_data = run_gpt5(str(front_prepped), str(back_prepped), hint_payload)
            except MissingAPIKey:
                log.event("post", sku, job_id=job_id, status="error", message="Missing AG5_API_KEY")
                response_data = _fake_model_response(sku, hint_payload.get("capsule", {}))
            except Exception as exc:  # pragma: no cover - defensive
                log.event("post", sku, job_id=job_id, status="error", message=str(exc))
                response_data = _fake_model_response(sku, hint_payload.get("capsule", {}))
        else:
            response_data = _fake_model_response(sku, hint_payload.get("capsule", {}))

        try:
            record = _normalise(response_data)
        except ValidationError as exc:
            log.event("post", sku, job_id=job_id, status="schema_error", message=str(exc))
            record = _normalise(_fake_model_response(sku, hint_payload.get("capsule", {})))
        needs_review = _needs_retry(record)

        if needs_review and config.get("provider") == "GPT-5 Vision":
            nudge_payload = dict(hint_payload)
            nudge_payload["nudge"] = _build_nudge(record, hint_payload.get("capsule", {}))
            nudge_payload["exemplars"] = (hint_payload.get("exemplars") or [])[:1]
            try:
                retry_raw = run_gpt5(str(front_prepped), str(back_prepped), nudge_payload)
                retry_record = _normalise(retry_raw)
                retry_review = _needs_retry(retry_record)
                if not retry_review or retry_record.get("conf", 0) >= record.get("conf", 0):
                    record = retry_record
                    needs_review = retry_review
            except Exception as exc:  # pragma: no cover - defensive
                log.event("post", sku, job_id=job_id, status="retry_error", message=str(exc))

        _write_outputs(result_root, sku, record, needs_review)
        summary = _summarise(record, needs_review)
        log.event("post", sku, job_id=job_id, status="needs_review" if needs_review else "ok", summary=summary)
        print(f"[POST] {sku}: {summary}")

    return str(result_root)
