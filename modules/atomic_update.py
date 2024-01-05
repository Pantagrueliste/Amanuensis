import orjson
from atomicwrites import atomic_write
from logging_config import get_logger
from json import JSONDecodeError

logger = get_logger(__name__)

def atomic_write_json(data, file_path, temp_dir='tmp/'):
    try:
        logger.info(f"Attempting to write JSON data to file: {file_path}")
        with atomic_write(file_path, overwrite=True, mode='wb', dir=temp_dir) as f:
            f.write(orjson.dumps(data))
        logger.info(f"Successfully wrote JSON data to file: {file_path}")
    except Exception as e:
        logger.exception(f"Error writing JSON data to file {file_path}: {e}")

def atomic_write_text(data, file_path, temp_dir='tmp/'):
    try:
        logger.info(f"Attempting to write text data to file: {file_path}")
        with atomic_write(file_path, overwrite=True, mode='w', encoding='utf-8', dir=temp_dir) as f:
            f.write(data)
        logger.info(f"Successfully wrote text data to file: {file_path}")
    except Exception as e:
        logger.exception(f"Error writing text data to file {file_path}: {e}")

def atomic_append_json(new_data, file_path, temp_dir='tmp/'):
    try:
        with open(file_path, 'r') as f:
            existing_data = orjson.loads(f.read())
            logger.info(f"Existing data loaded from {file_path}.")
    except FileNotFoundError:
        existing_data = {}
        logger.error(f"File {file_path} not found. Creating new file.")
    except JSONDecodeError as e:
        logger.exception(f"JSON decode error in file {file_path}: {e}")
        existing_data = {}

    merged_data = {**existing_data, **new_data}

    try:
        with atomic_write(file_path, overwrite=True, mode='wb', dir=temp_dir) as f:
            f.write(orjson.dumps(merged_data))
        logger.info(f"Successfully appended JSON data to file: {file_path}")
    except Exception as e:
        logger.exception(f"Error appending JSON data to file {file_path}: {e}")
