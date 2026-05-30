from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from pathlib import Path

from .utils import ensure_dir


def setup_logger(config: dict | None = None, name: str = "math_graphrag") -> logging.Logger:
    config = config or {}
    log_cfg = config.get("logging", {})
    level = getattr(logging, str(log_cfg.get("level", "INFO")).upper(), logging.INFO)
    log_file = log_cfg.get("file")

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    if log_file:
        p = Path(log_file)
        ensure_dir(p.parent)
        fh = logging.FileHandler(p, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


@contextmanager
def log_stage(logger: logging.Logger, stage_name: str):
    start = time.time()
    logger.info("START %s", stage_name)
    try:
        yield
        logger.info("END %s | %.2fs", stage_name, time.time() - start)
    except Exception:
        logger.exception("FAILED %s | %.2fs", stage_name, time.time() - start)
        raise
