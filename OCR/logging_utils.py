"""Consistent JSON event records without document text or exception messages."""
import json
import logging


def log_event(logger: logging.Logger, event: str, *, level: int = logging.INFO, **fields) -> None:
    logger.log(level, json.dumps({"event": event, **fields}, ensure_ascii=False))
