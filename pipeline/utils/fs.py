import os, shutil, tempfile, hashlib

def ensure_dir(path:str):
    os.makedirs(path, exist_ok=True)

def atomic_move(src:str, dst:str):
    ensure_dir(os.path.dirname(dst) or ".")
    tmp = dst + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)

def checksum(path:str, algo='md5'):
    h = hashlib.new(algo)
    with open(path,'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()
