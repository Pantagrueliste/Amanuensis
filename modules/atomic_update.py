import orjson
from atomicwrites import atomic_write
from logging_config import get_logger

logger = get_logger(__name__)

def atomic_write_json(data, file_path, temp_dir='tmp/'):
    with atomic_write(file_path, overwrite=True, mode='wb', dir=temp_dir) as f:
        f.write(orjson.dumps(data))


def atomic_write_text(data, file_path, temp_dir='tmp/'):
    with atomic_write(file_path, overwrite=True, mode='w', encoding='utf-8', dir=temp_dir) as f:
        f.write(data)
        logger.debug(f"Writing to file: {file_path}")


def atomic_append_json(new_data, file_path, temp_dir='tmp/'):
    try:
        with open(file_path, 'r') as f:
            existing_data = orjson.loads(f.read())
    except FileNotFoundError:
        existing_data = {}

    merged_data = {**existing_data, **new_data}

    with atomic_write(file_path, overwrite=True, mode='wb', dir=temp_dir) as f:
        f.write(orjson.dumps(merged_data))
