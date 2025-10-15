import os, re, time, shutil
from pipeline.utils import fs, naming, log

def find_pairs(inbox):
    files = [f for f in os.listdir(inbox) if os.path.isfile(os.path.join(inbox,f))]
    # Expect pattern: <base>_<F|B>.<ext>
    d = {}
    for f in files:
        m = re.match(r'^(.*)_(F|B)\.(jpg|jpeg|png|tif|tiff)$', f, re.IGNORECASE)
        if not m: 
            continue
        base, side, ext = m.groups()
        d.setdefault(base, {})[side.upper()] = f
    return [(base, sides['F'], sides['B']) for base, sides in d.items() if 'F' in sides and 'B' in sides]

def process(inbox='Scans_Inbox', ready='Scans_Ready', error='Scans_Error'):
    os.makedirs(inbox, exist_ok=True)
    os.makedirs(ready, exist_ok=True)
    os.makedirs(error, exist_ok=True)
    pairs = find_pairs(inbox)
    moved = 0
    for base, fF, fB in pairs:
        try:
            sku = base
            naming.parse_sku(base)  # validate
            dst_dir = os.path.join(ready, sku)
            fs.ensure_dir(dst_dir)
            fs.atomic_move(os.path.join(inbox,fF), os.path.join(dst_dir, fF))
            fs.atomic_move(os.path.join(inbox,fB), os.path.join(dst_dir, fB))
            with open(os.path.join(dst_dir,'pair.json'),'w') as fp:
                fp.write('{"status":"paired"}')
            log.event('pair', sku, moved=2)
            moved += 1
        except Exception as e:
            # move to error
            err_dir = os.path.join(error, base.replace('/','_'))
            fs.ensure_dir(err_dir)
            for fn in [fF,fB]:
                src = os.path.join(inbox,fn)
                if os.path.exists(src):
                    fs.atomic_move(src, os.path.join(err_dir, fn))
            with open(os.path.join(err_dir,'error.txt'),'w') as fp:
                fp.write(str(e))
            log.event('pair', base, status='error', msg=str(e))
    return moved
