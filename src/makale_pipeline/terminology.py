"""Terminoloji: terim adayı çıkarma + külliyat geneli tutarlılık."""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path

from makale_pipeline import DOCUMENTS_DIR
from makale_pipeline.config import load_config
from makale_pipeline.paths import find_source_files, target_path_for_source
from makale_pipeline.structured import is_structured_document, parse_document
from makale_pipeline.translation_qa import _acronyms, _capitalized_frequent

_QUOTED_RE = re.compile(r"[\"\"«»]([^\"\"«»]{3,60})[\"\"«»]")
_MIN_FREQ = 3
_TOP_N = 40


def extract_candidates(source_path: Path | str, top: int = _TOP_N) -> dict:
    """Kaynaktan sözlük adayı terimler çıkarır (sıklık + kısaltma + tırnak içi)."""
    src = Path(source_path)
    if not src.exists():
        return {"ok": False, "error": f"Kaynak yok: {src}"}
    text = src.read_text(encoding="utf-8")
    doc = parse_document(text) if is_structured_document(text) else None
    body = doc.body_text() if doc else text

    config = load_config(src.parent)
    known = {str(k).lower() for k in (config.get("glossary", {}) or {})}

    scored: Counter = Counter()
    for token, count in _capitalized_frequent(body, min_freq=2).items():
        if token.lower() not in known:
            scored[token] += count * 2
    for token, count in _acronyms(body).items():
        if token.lower() not in known:
            scored[token] += count * 3
    for m in _QUOTED_RE.finditer(body):
        term = m.group(1).strip()
        if len(term.split()) <= 4 and term.lower() not in known:
            scored[term] += 2

    cands = [
        {"term": t, "count": c}
        for t, c in scored.most_common(top) if c >= _MIN_FREQ
    ]
    return {"ok": True, "source": src.name, "candidates": cands}


def add_to_glossary(source_path: Path | str, entries: dict[str, str]) -> dict:
    """Seçili terimleri belgenin config.json sözlüğüne ekler."""
    src = Path(source_path)
    cfg_path = src.parent / "config.json"
    data: dict = {}
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    gloss = data.get("glossary", {}) or {}
    added = [k for k in entries if k not in gloss]
    gloss.update(entries)
    data["glossary"] = gloss
    cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "config": str(cfg_path), "added": added,
            "terms": len(gloss)}


def corpus_consistency(docs_dir: Path | None = None) -> dict:
    """Külliyatta sözlük terimlerinin belge bazında kapsama matrisi.

    Aynı terimin bazı belgelerde karşılıksız kalması (= farklı çeviri
    olasılığı) satır satır görünür.
    """
    from makale_pipeline.translation_qa import check_glossary_coverage

    docs_dir = Path(docs_dir or DOCUMENTS_DIR)
    matrix: dict[str, dict[str, str]] = {}
    docs_seen: list[str] = []
    if docs_dir.is_dir():
        for root, _, files in os.walk(docs_dir):
            p = Path(root)
            for src in find_source_files(p):
                tr = target_path_for_source(src)
                if not tr.exists():
                    continue
                try:
                    src_raw, tr_raw = src.read_text(encoding="utf-8"), tr.read_text(encoding="utf-8")
                    if not is_structured_document(src_raw) or not is_structured_document(tr_raw):
                        continue
                    source, target = parse_document(src_raw), parse_document(tr_raw)
                except OSError:
                    continue
                gloss = load_config(p).get("glossary", {}) or {}
                if not gloss:
                    continue
                rel = str(p.relative_to(docs_dir))
                docs_seen.append(rel)
                bad_terms = set()
                for w in check_glossary_coverage(source, target, gloss):
                    m = re.search(r"'([^']+)' ->", w)
                    if m:
                        bad_terms.add(m.group(1))
                for term in gloss:
                    matrix.setdefault(str(term), {})[rel] = (
                        "eksik" if str(term) in bad_terms else "ok"
                    )
    inconsistent = {t: d for t, d in matrix.items()
                    if any(v == "eksik" for v in d.values())}
    return {"ok": True, "documents": sorted(set(docs_seen)), "terms": len(matrix),
            "inconsistent": inconsistent}
