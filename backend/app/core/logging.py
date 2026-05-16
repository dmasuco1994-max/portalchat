"""Minimal logging setup so app warnings/errors actually show up in `docker compose logs`.

Uvicorn already configures its own loggers; we just install a sane default
handler for our `app.*` namespace and pin the level to INFO. This is a
30-second setup — full structured logging belongs in a later phase.
"""
import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    app_logger = logging.getLogger("app")
    # Avoid duplicating handlers on uvicorn --reload
    if not any(isinstance(h, logging.StreamHandler) for h in app_logger.handlers):
        app_logger.addHandler(handler)
    app_logger.setLevel(level)
    app_logger.propagate = False
