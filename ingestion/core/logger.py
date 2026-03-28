import logging
import colorlog
from functools import lru_cache
from ingestion.core.config import get_settings

def _build_logger(name: str) -> logging.Logger:
    settings = get_settings()

    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        fmt = "%(log_color)s%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt = "%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG":    "cyan",
            "INFO":     "green",
            "WARNING":  "yellow",
            "ERROR":    "red",
            "CRITICAL": "bold_red",
        }
    ))

    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level.upper())
    logger.addHandler(handler)
    logger.propagate = False

    return logger

@lru_cache
def get_logger(name: str) -> logging.Logger:
    return _build_logger(name)