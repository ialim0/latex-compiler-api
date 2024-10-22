import logging
from typing import Any, Dict
import json

class CustomJSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if hasattr(record, "props"):
            log_record.update(record.props)
        return json.dumps(log_record)

def setup_logging() -> None:
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(CustomJSONFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
