"""Kütüphane indeksi: gerçek tam metin indeksi (index.json) + arama.

İndeks, her dosyanın küçük harfli metnini ve mtime/size damgasını saklar;
arama dosyaları tekrar okumadan indeks üzerinden yapılır. Damgası değişen
dosya aramada tazelenir.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from makale_pipeline import DOCUMENTS_DIR, PROJECT_ROOT

INDEX_FILE = DOCUMENTS_DIR / "index.json"
MAX_SNIPPETS_PER_FILE = 5


def _entry_for(fp: Path) -> dict | None:
    try:
        st = fp.stat()
        text = fp.read_text(encoding="utf-8")
    except OSError:
        return None
    return {
        "mtime": st.st_mtime,
        "size": st.st_size,
        "chars": len(text),
        "text": text.lower(),
    }


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
                entry = _entry_for(fp)
                if entry is not None:
                    entries[rel] = entry
    docs_dir.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(
        json.dumps({"entries": entries}, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"indexed": len(entries), "index": str(INDEX_FILE)}


def _load_entries() -> dict[str, dict]:
    if INDEX_FILE.exists():
        try:
            data = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            if isinstance(data.get("entries"), dict):
                return data["entries"]
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def search(query: str, limit: int = 20, rebuild: bool = False) -> list[dict]:
    """İndeks üzerinden büyük/küçük harf duyarsız arama; alıntılı sonuçlar."""
    query = query.strip().lower()
    if not query:
        return []
    if rebuild or not INDEX_FILE.exists():
        build_index()
    entries = _load_entries()
    hits: list[dict] = []
    dirty = False
    for rel, entry in entries.items():
        fp = Path(PROJECT_ROOT) / rel
        if not fp.exists():
            continue
        try:
            st = fp.stat()
        except OSError:
            continue
        text = entry.get("text", "")
        if entry.get("mtime") != st.st_mtime or entry.get("size") != st.st_size:
            fresh = _entry_for(fp)
            if fresh is None:
                continue
            entries[rel] = fresh
            text = fresh["text"]
            dirty = True
        for m in re.finditer(re.escape(query), text):
            start = max(0, m.start() - 80)
            end = min(len(text), m.end() + 80)
            snippet = " ".join(text[start:end].split())
            hits.append({"file": rel, "snippet": snippet})
            if len([h for h in hits if h["file"] == rel]) >= MAX_SNIPPETS_PER_FILE:
                break
            if len(hits) >= limit:
                break
        if len(hits) >= limit:
            break
    if dirty:
        try:
            INDEX_FILE.write_text(
                json.dumps({"entries": entries}, ensure_ascii=False), encoding="utf-8"
            )
        except OSError:
            pass
    return hits[:limit]
