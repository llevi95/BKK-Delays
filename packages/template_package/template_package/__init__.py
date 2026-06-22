"""This init file defines a JSON logger on package level.
It configures the logger to output log records in JSON format,
Use it anywhere like this: `from template_package import logger`"""

import logging
from pythonjsonlogger import json
import dotenv

dotenv.load_dotenv()


# create a custom JSON formatter to remove null values
class CustomJsonFormatter(json.JsonFormatter):
    """Custom JSON formatter that removes null values from log records."""

    def process_log_record(self, log_record):
        """Process the log record to remove keys with None values."""
        return {key: value for key, value in log_record.items() if value is not None}


# Configure logger
logger = logging.getLogger("template_package")
logger.setLevel(logging.INFO)

# Add a JSON formatter to the logger
if not logger.hasHandlers():
    stream_handler = logging.StreamHandler()
    json_formatter = CustomJsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s %(method)s %(query)s %(rows)s %(execution_time)s",
        json_ensure_ascii=False,
    )
    stream_handler.setFormatter(json_formatter)
    # Ensure UTF-8 encoding for the log stream
    try:
        stream_handler.stream.reconfigure(encoding="utf-8")
    except AttributeError:
        logger.info("Logging encoder could not be set to utf-8.")
        pass
    logger.addHandler(stream_handler)


