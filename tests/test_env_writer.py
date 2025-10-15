import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_write_env_overwrites_existing(tmp_path):
    env_path = tmp_path / '.env'
    env_path.write_text('AG5_API_KEY=old\nMODEL_NAME=gpt-4\nAG5_API_KEY=older\n', encoding='utf-8')

    preload_path = json.dumps(str((REPO_ROOT / 'preload.js').resolve()))
    root_arg = json.dumps(str(tmp_path.resolve()))
    script = tmp_path / 'env_test.js'
    script.write_text(
        '\n'.join(
            [
                f"const preload = require({preload_path});",
                "const path = require('path');",
                f"const root = {root_arg};",
                "preload.writeEnv(root, { AG5_API_KEY: 'newkey', MODEL_NAME: 'gpt-5.1-vision' });",
                "const fs = require('fs');",
                "process.stdout.write(fs.readFileSync(path.join(root, '.env'), 'utf8'));",
            ]
        ),
        encoding='utf-8',
    )

    result = subprocess.run(['node', str(script)], check=True, capture_output=True, text=True)
    lines = [line for line in result.stdout.strip().split('\n') if line]

    ag5_lines = [line for line in lines if line.startswith('AG5_API_KEY=')]
    model_lines = [line for line in lines if line.startswith('MODEL_NAME=')]

    assert len(ag5_lines) == 1
    assert ag5_lines[0] == 'AG5_API_KEY=newkey'
    assert len(model_lines) == 1
    assert model_lines[0] == 'MODEL_NAME=gpt-5.1-vision'
