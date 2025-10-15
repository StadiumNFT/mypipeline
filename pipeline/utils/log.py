import json, os, time

LOG_PATH = 'pipeline/logs/pipeline.jsonl'

def event(step, sku=None, status='ok', **kw):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    rec = {'ts': time.time(), 'step': step, 'sku': sku, 'status': status}
    rec.update(kw)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')
