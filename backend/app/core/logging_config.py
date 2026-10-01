import json
import logging
import sys
from datetime import UTC, datetime

# Attribute names present on every vanilla LogRecord, plus uvicorn's own
# "color_message" (raw ANSI codes for its colorized console formatter, which
# we don't use). Used to find the "extra={...}" fields a caller actually
# added, so they can be surfaced as their own JSON keys instead of getting
# lost inside a formatted message string.
_STANDARD_ATTRS = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
    "color_message"
}


class JsonFormatter(logging.Formatter):
    """One JSON object per line, for every log source in the process.

    App code, uvicorn's own access/error loggers, Alembic, and gunicorn's
    master/worker lifecycle messages each use a different default text
    format. Rendering all of them through this one formatter (see
    configure_logging() below and backend/logging.json, which points
    gunicorn's own loggers at this same class) gives a log aggregator one
    consistent, machine-parseable shape to index instead of several
    incompatible ones mixed in the same stream.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
