"""Application logging configuration."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a logger using the standard library logging API."""
    return logging.getLogger(name)
