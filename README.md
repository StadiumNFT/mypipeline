# mypipeline

Ageless Collectibles AI card scanner pipeline.

## Overview

This project provides a command line pipeline that:

1. Discovers scanned card images inside a `Scans_Inbox` directory.
2. Pairs the front and back scans for each card using filename heuristics.
3. Sends the paired scans to the GPT-5 multimodal API to extract structured card metadata.
4. Applies optional rule-based classifications to each card.
5. Persists the per-card payloads and an aggregated summary to disk.

The tooling is designed so it can be run in a "dry run" mode which produces synthetic responses for development environments without GPT credentials.

## Installation

```bash
pip install -e .
```

This installs the `card-pipeline` console script that exposes the pipeline commands.

## Usage

### Prepare folders

Ensure your scans follow the structure:

```
scans/
└── Scans_Inbox/
    ├── michael_jordan_front.jpg
    ├── michael_jordan_back.jpg
    ├── kobe_front.png
    └── kobe_back.png
```

The pipeline attempts to automatically pair scans based on filename patterns such as `front`, `back`, `f`, `b`, `obverse`, and `reverse`.

### Dry run (no GPT calls)

```bash
card-pipeline run --dry-run
```

This command will generate mock extraction data and store the payloads under `scans/Processed` as well as a summary JSON file at `scans/results.json`.

### Full run

```bash
export OPENAI_API_KEY=sk-...
card-pipeline run
```

Optional flags:

- `--scans-inbox`: Override the inbox folder.
- `--processed-output`: Change where individual payload JSON files are written.
- `--results-output`: Change the summary JSON path.
- `--classification-rules`: Provide a JSON/YAML file containing classification rules.
- `--model`: Override the GPT-5 model identifier.
- `--max-parallel-requests`: Control concurrency for future enhancements.

### Inspect detected pairs

```bash
card-pipeline pair
```

This prints the list of paired scans without contacting the GPT API.

## Classification Rules

Classification rules are optional and accept JSON or YAML documents. A minimal example looks like:

```json
{
  "rules": [
    {
      "label": "High Value",
      "confidence": 0.9,
      "reasons": ["Gem Mint condition"],
      "criteria": [
        {"field": "condition", "equals": "Gem Mint"},
        {"field": "attributes.grade", "equals": "PSA 10"}
      ]
    }
  ]
}
```

The classifier evaluates rules in order and assigns the first matching label to the card. Each criterion supports the following operations:

- `equals`
- `contains`
- `in`
- `greater_than`
- `less_than`

Fields refer to keys in the extraction result (e.g. `attributes.grade`).

## Development notes

- The GPT client uses the [`openai`](https://github.com/openai/openai-python) package and expects GPT-5 multimodal endpoints to be available.
- When running in environments without GPT access, pass `--dry-run` to return deterministic mock data.
- Optional YAML rule files require `PyYAML` to be installed manually.
