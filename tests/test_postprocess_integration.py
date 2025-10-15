import csv
import json
from pathlib import Path

from PIL import Image

from pipeline import postprocess


def _make_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new('RGB', (32, 32), color='white')
    img.save(path)


def test_process_batch_mock_provider(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    ready_dir = tmp_path / 'Scans_Ready'
    sku = 'Box1-AA_0001'
    front_path = ready_dir / sku / f'{sku}_F.jpg'
    back_path = ready_dir / sku / f'{sku}_B.jpg'
    _make_image(front_path)
    _make_image(back_path)

    batches_dir = tmp_path / 'pipeline' / 'output' / 'batches'
    batches_dir.mkdir(parents=True)
    job_id = 'batch_test'
    with (batches_dir / f'{job_id}.jsonl').open('w', encoding='utf-8') as handle:
        payload = {'sku': sku, 'images': [front_path.name, back_path.name]}
        handle.write(json.dumps(payload) + '\n')

    config_path = tmp_path / 'pipeline' / 'config' / 'model.json'
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps({'provider': 'Mock'}), encoding='utf-8')

    monkeypatch.setattr(postprocess, 'CONFIG_PATH', config_path)
    monkeypatch.setattr(postprocess, 'TMP_DIR', tmp_path / 'pipeline' / 'tmp')

    result_root = Path(
        postprocess.process_batch(
            job_id,
            ready=str(ready_dir),
            batches=str(batches_dir),
            outroot=str(tmp_path / 'pipeline' / 'output'),
        )
    )

    csv_path = result_root / 'csv' / 'batch.csv'
    assert csv_path.exists()

    with csv_path.open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    row = rows[0]
    assert row['sku'] == sku
    assert row['cat'] in {'sports', 'marvel', 'pokemon', 'other'}
    assert row['needs_review'] in {'True', 'False'}

    txt_path = result_root / 'txt' / f'{sku}.txt'
    assert txt_path.exists()
