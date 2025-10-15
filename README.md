Ageless Pipeline (MVP)

How to run (local):
1) Put image pairs into Scans_Inbox using your naming: Box3-BD_0001_F.jpg and Box3-BD_0001_B.jpg
2) Pair to Scans_Ready:
   python -m pipeline.run pair
3) Create a batch (returns a job id):
   python -m pipeline.run queue --batch-size 20
4) Post-process a batch (uses mock model until API wired):
   python -m pipeline.run post --job-id <printed_id>

### Windows one-click UI

Prefer a guided experience? Use the batch files in `scripts/windows` to run each
stage via a double-click. See [Windows One-Click Pipeline UI](docs/windows_ui_pipeline.md)
for details.

Outputs:
- pipeline/output/json/<SKU>.json
- pipeline/output/txt/<SKU>.txt
- pipeline/output/csv/bulk_upload_<job>.csv

Note: postprocess uses a deterministic mock. Swap fake_model_response() with real API call.
