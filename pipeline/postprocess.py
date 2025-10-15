import os, json, time, pathlib, csv
from pipeline.utils import log
from pipeline.utils import naming

def _choose_template(cat:str):
    if cat.lower().startswith('marvel'): return 'marvel'
    if cat.lower().startswith('sports'): return 'sports'
    if cat.lower().startswith('tcg'): return 'tcg'
    return 'general'

def fake_model_response(sku, images):
    # Placeholder: a cheap deterministic mock so flow runs offline.
    base = naming.parse_sku(sku)
    cat = 'Marvel' if base['batch_code'] in {'BD','DG','MM'} else 'Sports'
    return {
        'sku': sku,
        'box_code': base['box'],
        'seq': base['seq'],
        'category': cat,
        'brand': 'Ageless',
        'set_name': 'Prototype',
        'year': 2025,
        'number': str(base['seq']),
        'player_or_character': 'TBD',
        'team': '',
        'parallel_or_insert': '',
        'grading_state': 'raw',
        'condition_notes': 'auto-generated placeholder',
        'confidence': 0.62,
        'price_min': 2.0,
        'price_max': 8.0,
        'csv_template': _choose_template(cat),
        'images': images,
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }

def process_batch(job_id, ready='Scans_Ready', batches='pipeline/output/batches', outroot='pipeline/output'):
    batch_file = os.path.join(batches, job_id + '.jsonl')
    if not os.path.exists(batch_file):
        raise FileNotFoundError(batch_file)
    json_dir = os.path.join(outroot,'json')
    txt_dir = os.path.join(outroot,'txt')
    csv_dir = os.path.join(outroot,'csv')
    os.makedirs(json_dir, exist_ok=True)
    os.makedirs(txt_dir, exist_ok=True)
    os.makedirs(csv_dir, exist_ok=True)

    rows = []
    with open(batch_file,'r',encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            sku = item['sku']
            resp = fake_model_response(sku, item['images'])
            with open(os.path.join(json_dir, sku+'.json'),'w',encoding='utf-8') as jf:
                json.dump(resp, jf, indent=2)
            with open(os.path.join(txt_dir, sku+'.txt'),'w',encoding='utf-8') as tf:
                tf.write(f"Category: {resp['category']} > {resp['set_name']} {resp['year']}\n")
                tf.write(resp['condition_notes'])
            # Prepare CSV row
            rows.append({
                'Title': f"{resp['year']} {resp['brand']} {resp['set_name']} #{resp['number']} {resp['player_or_character']}",
                'PriceMin': resp['price_min'],
                'PriceMax': resp['price_max'],
                'SKU': resp['sku'],
                'Category': resp['category'],
                'Template': resp['csv_template']
            })
            log.event('post', sku, job_id=job_id)
    # Write a single CSV aggregating rows
    csv_path = os.path.join(csv_dir, f'bulk_upload_{job_id}.csv')
    with open(csv_path,'w',newline='',encoding='utf-8') as cf:
        w = csv.DictWriter(cf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows: w.writerow(r)
    return csv_path
