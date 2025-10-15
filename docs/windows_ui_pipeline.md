# Windows One-Click Pipeline UI

This project now includes Windows batch scripts that provide a simple "one-click" UI for running each stage of the pipeline locally. The scripts live in `scripts/windows` and can be double-clicked from File Explorer.

## Prerequisites

Before using the scripts ensure:

1. Python is installed and available on the `PATH`.
2. The project dependencies have been installed (e.g. `pip install -e .`).
3. The working directory contains the expected folders (`Scans_Inbox`, `Scans_Ready`, etc.).

## Scripts

| Script | Purpose |
| --- | --- |
| `1_pair.bat` | Moves paired front/back scans from `Scans_Inbox` into `Scans_Ready`. |
| `2_queue.bat` | Prompts for a batch size (default 20) and creates batch jobs from `Scans_Ready`. |
| `3_postprocess.bat` | Prompts for a job id and post-processes that batch. |

Each script opens a command window, displays progress, and pauses at the end so you can review the output. Errors surface directly in the same window.

## Typical Workflow

1. Double-click `1_pair.bat` to pair scans.
2. When ready to build jobs, run `2_queue.bat` and accept the default batch size or enter a new value.
3. Copy one of the printed job ids and run `3_postprocess.bat`, pasting the id when prompted.

Repeat the queue and post-process steps as needed for additional jobs.

## Troubleshooting

- If the scripts cannot find Python, add it to your system `PATH` or edit the `.bat` files to point to the correct interpreter.
- Check the console output for detailed error messages if any step fails.
- Verify the folder structure matches the expectations outlined in the main README.
