import logging
import os
from config import Config

# Instantiate the Config class
config = Config()

# Define the logging format
log_format = "%(asctime)s - %(levelname)s - %(module)s: %(message)s"

# Get the logging level from the config
logging_level = getattr(logging, config.debug_level, logging.WARNING)

# Ensure the logs directory exists
if not os.path.exists("logs"):
    os.makedirs("logs")

# Set up the root logger
logging.basicConfig(
    level=logging_level,
    format=log_format,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/amanuensis.log", mode="a")
    ]
)

def get_logger(module_name):
    logger = logging.getLogger(module_name)
    # Configure your logger here (if needed)
    return logger
