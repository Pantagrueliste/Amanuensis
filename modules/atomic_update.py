import orjson
import logging
from atomicwrites import atomic_write


def atomic_write_json(data, file_path):
    with atomic_write(file_path, overwrite=True, mode='wb') as f:
        f.write(orjson.dumps(data))


def atomic_write_text(data, file_path):
    with atomic_write(file_path, overwrite=True, mode='w', encoding='utf-8') as f:
        f.write(data)
        logging.debug(f"Writing to file: {file_path}")


def atomic_append_json(new_data, file_path):
    try:
        with open(file_path, 'r') as f:
            existing_data = orjson.loads(f.read())
    except FileNotFoundError:
        existing_data = {}

    merged_data = {**existing_data, **new_data}

    with atomic_write(file_path, overwrite=True, mode='wb') as f:
        f.write(orjson.dumps(merged_data))
