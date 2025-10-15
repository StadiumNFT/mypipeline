"""Command-line entrypoint for the card processing pipeline."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer

from .card_pipeline import CardProcessingPipeline
from .config import PipelineConfig

logging.basicConfig(level=logging.INFO)

app = typer.Typer(help="Process scanned cards using the GPT-5 vision API.")


def _read_config(
    scans_inbox: Path,
    processed_output: Path,
    results_output: Path,
    dry_run: bool,
    classification_rules: Optional[Path],
    model: str,
    max_parallel_requests: int,
) -> PipelineConfig:
    kwargs = {
        "scans_inbox": scans_inbox,
        "processed_output": processed_output,
        "results_output": results_output,
        "dry_run": dry_run,
        "classification_rules_path": classification_rules,
        "api_model": model,
        "max_parallel_requests": max_parallel_requests,
    }
    return PipelineConfig(**kwargs)


@app.command("run")
def run_pipeline(
    scans_inbox: Path = typer.Option(Path("scans/Scans_Inbox"), help="Directory of raw scans."),
    processed_output: Path = typer.Option(Path("scans/Processed"), help="Directory for per-card payloads."),
    results_output: Path = typer.Option(Path("scans/results.json"), help="Summary JSON output."),
    classification_rules: Optional[Path] = typer.Option(None, help="Optional JSON/YAML classification rules."),
    model: str = typer.Option("gpt-5.0-vision-preview", help="GPT-5 model name to call."),
    dry_run: bool = typer.Option(False, help="Run without contacting the GPT API and emit synthetic data."),
    max_parallel_requests: int = typer.Option(2, min=1, help="Maximum GPT requests to issue in parallel."),
) -> None:
    """Run the pipeline end-to-end."""

    config = _read_config(
        scans_inbox,
        processed_output,
        results_output,
        dry_run,
        classification_rules,
        model,
        max_parallel_requests,
    )
    pipeline = CardProcessingPipeline(config)
    files = pipeline.discover_scan_files()
    pairs = pipeline.pair_scans(files)
    results = pipeline.process_pairs(pairs)
    typer.echo(json.dumps([result.dict() for result in results], indent=2, default=str))


@app.command("pair")
def pair_scans(
    scans_inbox: Path = typer.Option(Path("scans/Scans_Inbox"), help="Directory of raw scans."),
    dry_run: bool = typer.Option(True, help="Keep consistent signature with run command."),
) -> None:
    """List the detected card pairs without invoking GPT."""

    config = PipelineConfig(scans_inbox=scans_inbox, dry_run=dry_run)
    pipeline = CardProcessingPipeline(config)
    files = pipeline.discover_scan_files()
    pairs = pipeline.pair_scans(files)
    payload = [pair.as_payload() for pair in pairs]
    typer.echo(json.dumps(payload, indent=2))


if __name__ == "__main__":
    app()
