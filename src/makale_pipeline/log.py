"""Çalışma günlüğü: stderr + scratch/makale.log dosyasına kayıt."""

from __future__ import annotations

import logging
import sys

_configured = False


def get_logger(name: str = "makale") -> logging.Logger:
    global _configured
    logger = logging.getLogger(name)
    if _configured:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    stderr = logging.StreamHandler(sys.stderr)
    stderr.setFormatter(fmt)
    logger.addHandler(stderr)
    try:
        from makale_pipeline import SCRATCH_DIR

        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(str(SCRATCH_DIR / "makale.log"), encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        pass
    _configured = True
    return logger
