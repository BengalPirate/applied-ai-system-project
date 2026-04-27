"""
Centralized logging configuration.

The agent, retriever, evaluator, and guardrails all log through this module
so that traces appear in both stderr and logs/recommender.log.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(os.environ.get("MOODMATCH_LOG_DIR", "logs"))
LOG_FILE = LOG_DIR / "recommender.log"

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    root = logging.getLogger("moodmatch")
    root.setLevel(logging.DEBUG)
    root.propagate = False
    if not root.handlers:
        stream = logging.StreamHandler()
        stream.setLevel(os.environ.get("MOODMATCH_STREAM_LEVEL", "INFO"))
        stream.setFormatter(fmt)
        root.addHandler(stream)

        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=512_000, backupCount=2, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the moodmatch namespace."""
    _configure()
    short = name.split(".")[-1]
    return logging.getLogger(f"moodmatch.{short}")
