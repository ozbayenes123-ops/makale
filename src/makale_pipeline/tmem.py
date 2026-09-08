"""Çeviri belleği: onaylı paragraf çiftlerini saklar, benzerini önerir.

Bellek belge klasöründe `tm.json` olarak durur; kayıt bilinçli yapılır
(record), öneri difflib benzerliğiyle gelir (suggest).
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path

from makale_pipeline.structured import is_structured_document, parse_document

TM_FILE = "tm.json"
MIN_RATIO = 0.6


def _tm_path(doc_dir: Path) -> Path:
    return Path(doc_dir) / TM_FILE


def _load(doc_dir: Path) -> list[dict]:
    fp = _tm_path(doc_dir)
    if not fp.exists():
        return []
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def record(source_path: Path | str) -> dict:
    """Onaylı kaynak/hedef çiftinin paragraf eşleşmelerini belleğe yazar."""
    from makale_pipeline.paths import target_path_for_source
    from makale_pipeline.translation_qa import _align_paragraphs

    src = Path(source_path)
    tr = target_path_for_source(src)
    if not tr.exists():
        return {"ok": False, "error": f"Hedef yok: {tr.name}"}
    src_raw, tr_raw = src.read_text(encoding="utf-8"), tr.read_text(encoding="utf-8")
    if not is_structured_document(src_raw) or not is_structured_document(tr_raw):
        return {"ok": False, "error": "Yapılandırılmamış çift"}
    s_paras = [p.text for s in parse_document(src_raw).sections for p in s.paragraphs]
    t_paras = [p.text for s in parse_document(tr_raw).sections for p in s.paragraphs]
    mem = _load(src.parent)
    have = {(m["src"], m["tr"]) for m in mem}
    added = 0
    for i, j in _align_paragraphs(s_paras, t_paras):
        if j >= 0 and s_paras[i].strip() and t_paras[j].strip():
            if (s_paras[i], t_paras[j]) not in have:
                mem.append({"src": s_paras[i], "tr": t_paras[j]})
                added += 1
    _tm_path(src.parent).write_text(json.dumps(mem, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"ok": True, "memory": str(_tm_path(src.parent)), "added": added,
            "entries": len(mem)}


def suggest(doc_dir: Path | str, text: str, top: int = 3) -> dict:
    """Bellekte benzer kaynak cümle ara; karşılığını öner."""
    mem = _load(Path(doc_dir))
    scored = []
    for m in mem:
        r = difflib.SequenceMatcher(a=text, b=m["src"], autojunk=False).ratio()
        if r >= MIN_RATIO:
            scored.append((r, m))
    scored.sort(key=lambda x: -x[0])
    return {"ok": True, "entries": len(mem),
            "suggestions": [{"ratio": round(r, 2), "src": m["src"][:200],
                             "tr": m["tr"][:200]} for r, m in scored[:top]]}
