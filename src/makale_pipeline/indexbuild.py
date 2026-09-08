"""Kütüphane indeksi üretimi (build_index giriş noktası)."""

from __future__ import annotations

from pathlib import Path

from makale_pipeline.search import INDEX_FILE, build_index as _build

__all__ = ["build_index", "INDEX_FILE"]


def build_index(docs_dir: Path | None = None) -> dict:
    return _build(docs_dir)
