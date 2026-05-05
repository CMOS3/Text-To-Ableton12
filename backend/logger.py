import logging
import json
import traceback
from datetime import datetime
from typing import Any

class JsonFormatter(logging.Formatter):
    """Custom formatter to output structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_obj["exception"] = "".join(traceback.format_exception(*record.exc_info))

        # Add any extra kwargs passed to the logger
        if hasattr(record, "extra_data"):
            log_obj["data"] = getattr(record, "extra_data")

        return json.dumps(log_obj)

def get_json_logger(name: str) -> logging.Logger:
    """Returns a logger configured for JSON output."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        
    return logger
