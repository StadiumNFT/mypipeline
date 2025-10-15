import os, json, glob, time, uuid
from pipeline.utils import log

def build_batches(ready='Scans_Ready', out='pipeline/output/batches', batch_size=20):
    os.makedirs(out, exist_ok=True)
    skus = [d for d in os.listdir(ready) if os.path.isdir(os.path.join(ready,d))]
    skus.sort()
    batches = []
    for i in range(0, len(skus), batch_size):
        batch = skus[i:i+batch_size]
        if not batch: 
            continue
        job_id = f'batch_{int(time.time())}_{uuid.uuid4().hex[:8]}'
        payload = []
        for sku in batch:
            folder = os.path.join(ready, sku)
            imgs = sorted(glob.glob(os.path.join(folder, f"{sku}_*." + "*")))
            payload.append({'sku': sku, 'images': [os.path.basename(p) for p in imgs]})
        with open(os.path.join(out, job_id+'.jsonl'),'w',encoding='utf-8') as f:
            for item in payload:
                f.write(json.dumps(item)+'\n')
        batches.append(job_id)
        log.event('queue', None, job_id=job_id, count=len(payload))
    return batches
