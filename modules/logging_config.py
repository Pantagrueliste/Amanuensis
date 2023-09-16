import logging
import os

# Ensure the logs directory exists
if not os.path.exists("logs"):
    os.makedirs("logs")

# Define the logging format
log_format = "%(asctime)s - %(levelname)s - %(module)s: %(message)s"

# Set up the root logger
logging.basicConfig(
    level=logging.DEBUG,
    format=log_format,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/amanuensis.log", mode="a")
    ]
)

# Expose a method to get the logger
def get_logger(module_name):
    return logging.getLogger(module_name)
