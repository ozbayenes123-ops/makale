"""Proje istatistikleri: belge, çeviri, paragraf ve dipnot sayımları."""

from __future__ import annotations

import os
from pathlib import Path

from makale_pipeline import DOCUMENTS_DIR
from makale_pipeline.paths import find_source_files, target_path_for_source
from makale_pipeline.structured import is_structured_document, parse_document


def project_stats(docs_dir: Path | None = None) -> dict:
    docs_dir = Path(docs_dir or DOCUMENTS_DIR)
    stats = {
        "folders": 0,
        "sources": 0,
        "translated": 0,
        "compiled_docx": 0,
        "compiled_html": 0,
        "paragraphs": 0,
        "footnotes": 0,
    }
    if not docs_dir.is_dir():
        return stats
    for root, _, files in os.walk(docs_dir):
        p = Path(root)
        if p == docs_dir:
            continue
        sources = find_source_files(p)
        if not sources and "config.json" not in files:
            continue
        stats["folders"] += 1
        for src in sources:
            stats["sources"] += 1
            tr = target_path_for_source(src)
            if tr.exists():
                stats["translated"] += 1
                if (p / tr.name.replace(".txt", ".docx")).exists():
                    stats["compiled_docx"] += 1
                if (p / tr.name.replace(".txt", ".html")).exists():
                    stats["compiled_html"] += 1
                try:
                    raw = tr.read_text(encoding="utf-8")
                    if is_structured_document(raw):
                        doc = parse_document(raw)
                        stats["paragraphs"] += doc.paragraph_count
                        stats["footnotes"] += doc.footnote_count
                except OSError:
                    continue
    return stats
