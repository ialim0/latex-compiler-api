import logging
import json
from typing import Any, Dict, Optional, List
from datetime import datetime


class CustomJSONFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": self._format_timestamp(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }

        props = getattr(record, "props", {})
        if isinstance(props, dict):
            log_record.update(props)

        return json.dumps(log_record, separators=(',', ':'))

    @staticmethod
    def _format_timestamp(record: logging.LogRecord) -> str:
        dt = datetime.utcfromtimestamp(record.created)
        return dt.isoformat() + 'Z'


class LoggerConfigurator:

    def __init__(
        self,
        level: int = logging.INFO,
        handlers: Optional[List[logging.Handler]] = None,
        formatter: Optional[logging.Formatter] = None,
    ):
        self.level = level
        self.handlers = handlers if handlers is not None else [logging.StreamHandler()]
        self.formatter = formatter if formatter is not None else CustomJSONFormatter()

    def configure(self) -> None:
        logger = logging.getLogger()
        logger.setLevel(self.level)

        if not logger.handlers:
            for handler in self.handlers:
                handler.setFormatter(self.formatter)
                handler.setLevel(self.level)
                logger.addHandler(handler)
        else:
            for handler in logger.handlers:
                if not isinstance(handler.formatter, CustomJSONFormatter):
                    handler.setFormatter(self.formatter)
                handler.setLevel(self.level)


def setup_logging(
    level: int = logging.INFO,
    handlers: Optional[List[logging.Handler]] = None,
    formatter: Optional[logging.Formatter] = None
) -> None:
    configurator = LoggerConfigurator(level=level, handlers=handlers, formatter=formatter)
    configurator.configure()
