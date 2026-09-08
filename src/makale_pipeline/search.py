"""Kütüphane indeksi: documents/index.json üretimi ve tam metin arama."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from makale_pipeline import DOCUMENTS_DIR, PROJECT_ROOT

INDEX_FILE = DOCUMENTS_DIR / "index.json"


def build_index(docs_dir: Path | None = None) -> dict:
    """Tüm txt belgeleri tarayıp index.json yazar; özet döndürür."""
    docs_dir = Path(docs_dir or DOCUMENTS_DIR)
    entries: dict[str, dict] = {}
    if docs_dir.is_dir():
        for root, _, files in os.walk(docs_dir):
            p = Path(root)
            for file in files:
                if not file.endswith(".txt"):
                    continue
                fp = p / file
                try:
                    rel = str(fp.relative_to(PROJECT_ROOT))
                except ValueError:
                    rel = str(fp)
                try:
                    text = fp.read_text(encoding="utf-8")
                except OSError:
                    continue
                entries[rel] = {"chars": len(text), "lines": text.count("\n") + 1}
    docs_dir.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(
        json.dumps({"entries": entries}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return {"indexed": len(entries), "index": str(INDEX_FILE)}


def _load_paths() -> list[Path]:
    if INDEX_FILE.exists():
        try:
            data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            return [Path(PROJECT_ROOT) / r for r in data.get("entries", {})]
        except (json.JSONDecodeError, OSError):
            pass
    docs_dir = DOCUMENTS_DIR
    out: list[Path] = []
    if docs_dir.is_dir():
        out = sorted(docs_dir.rglob("*_tr.txt"))
    return out


def search(query: str, limit: int = 20, rebuild: bool = False) -> list[dict]:
    """Çevirilerde büyük/küçük harf duyarsız arama; alıntılı sonuçlar."""
    query = query.strip()
    if not query:
        return []
    if rebuild or not INDEX_FILE.exists():
        build_index()
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    hits: list[dict] = []
    for fp in _load_paths():
        if not fp.exists():
            continue
        try:
            text = fp.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in pattern.finditer(text):
            start = max(0, m.start() - 80)
            end = min(len(text), m.end() + 80)
            snippet = " ".join(text[start:end].split())
            try:
                rel = str(fp.relative_to(PROJECT_ROOT))
            except ValueError:
                rel = str(fp)
            hits.append({"file": rel, "snippet": snippet})
            if len(hits) >= limit:
                return hits
    return hits
