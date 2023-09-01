import json
from atomicwrites import atomic_write

def atomic_write_json(data, file_path):
    with atomic_write(file_path, overwrite=True, mode='w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
