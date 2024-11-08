import orjson
from atomicwrites import atomic_write
from logging_config import get_logger
from json import JSONDecodeError
import json

logger = get_logger(__name__)

def atomic_write_json(data, file_path, temp_dir='tmp/'):
    try:
        logger.info(f"Attempting to write JSON data to file: {file_path}")
        with atomic_write(file_path, overwrite=True, mode='wb', dir=temp_dir) as f:
            f.write(json.dumps(data, indent=4).encode('utf-8'))
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
            f.write(json.dumps(merged_data, indent=4).encode('utf-8'))
        logger.info(f"Successfully appended JSON data to file: {file_path}")
    except Exception as e:
        logger.exception(f"Error appending JSON data to file {file_path}: {e}")

def atomic_append_dict(new_data, file_path, temp_dir='tmp/'):
    try:
        # Attempt to load existing data from the file
        with open(file_path, 'r') as f:
            existing_data = orjson.loads(f.read())
            logger.info(f"Existing data loaded from {file_path}.")
    except FileNotFoundError:
        # If the file doesn't exist, start with an empty dictionary
        existing_data = {}
        logger.info(f"File {file_path} not found. Creating new file.")
    except orjson.JSONDecodeError as e:
        # Handle JSON decoding errors
        logger.exception(f"JSON decode error in file {file_path}: {e}")
        existing_data = {}

    # Ensure both existing_data and new_data are dictionaries
    if not isinstance(existing_data, dict):
        logger.error(f"Existing data in {file_path} is not a dictionary.")
        return
    if not isinstance(new_data, dict):
        logger.error("New data provided is not a dictionary.")
        return

    # Merge new_data into existing_data
    existing_data.update(new_data)

    try:
        # Write the merged data back to the file atomically
        with atomic_write(file_path, overwrite=True, mode='wb', dir=temp_dir) as f:
            f.write(json.dumps(existing_data, indent=4).encode('utf-8'))
        logger.info(f"Successfully updated JSON data in file: {file_path}")
    except Exception as e:
        logger.exception(f"Error updating JSON data in file {file_path}: {e}")
