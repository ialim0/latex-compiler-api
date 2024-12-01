# app/core/logging.py
import logging
import json
from typing import Any, Dict, Optional, List
from datetime import datetime


class CustomJSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Formats log records as JSON strings with essential fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: JSON-formatted log record.
        """
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
        """
        Format the timestamp in ISO 8601 format with UTC timezone.

        Args:
            record (logging.LogRecord): The log record.

        Returns:
            str: Formatted timestamp.
        """
        dt = datetime.utcfromtimestamp(record.created)
        return dt.isoformat() + 'Z'


class LoggerConfigurator:
    """
    Configures the root logger with a custom JSON formatter and specified handlers.
    """

    def __init__(
        self,
        level: int = logging.INFO,
        handlers: Optional[List[logging.Handler]] = None,
        formatter: Optional[logging.Formatter] = None,
    ):
        """
        Initialize the LoggerConfigurator.

        Args:
            level (int): Logging level. Defaults to logging.INFO.
            handlers (Optional[List[logging.Handler]]): List of logging handlers. 
                Defaults to [StreamHandler()].
            formatter (Optional[logging.Formatter]): Formatter to use. 
                Defaults to CustomJSONFormatter().
        """
        self.level = level
        self.handlers = handlers if handlers is not None else [logging.StreamHandler()]
        self.formatter = formatter if formatter is not None else CustomJSONFormatter()

    def configure(self) -> None:
        """
        Configure the root logger with the specified handlers and formatter.
        Prevents adding multiple handlers if already configured.
        """
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
    """
    Convenience function to configure logging using LoggerConfigurator.

    Args:
        level (int): Logging level. Defaults to logging.INFO.
        handlers (Optional[List[logging.Handler]]): List of logging handlers. 
            Defaults to [StreamHandler()].
        formatter (Optional[logging.Formatter]): Formatter to use. 
            Defaults to CustomJSONFormatter().
    """
    configurator = LoggerConfigurator(level=level, handlers=handlers, formatter=formatter)
    configurator.configure()
