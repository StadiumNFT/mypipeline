import re
SKU_RE = re.compile(r'^(Box\d+)-([A-Z]{2})_(\d{4})$')

def parse_sku(base:str):
    m = SKU_RE.match(base)
    if not m:
        raise ValueError(f'Invalid SKU base: {base}')
    box, batch, seq = m.groups()
    return {'box': box, 'batch_code': batch, 'seq': int(seq)}
