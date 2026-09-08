"""Atıf denetimi ve kaynakça üretimi.

citation_check: metin-içi [fn N] gönderimleri ile [FOOTNOTES] listesinin
birebir eşleşmesi, tanımsız/fazla dipnot, sıra bozukluğu.
bibliography: dipnot listesinden tekilleştirilmiş kaynakça üretir.
"""

from __future__ import annotations

import re
from pathlib import Path

from makale_pipeline.structured import extract_fn_refs, is_structured_document, parse_document

_SHORT_TITLE_RE = re.compile(r"^(.{10,80}?)(\.|,)\s")


def citation_check(tr_path: Path | str) -> dict:
    p = Path(tr_path)
    if not p.exists():
        return {"ok": False, "error": f"Dosya yok: {p}"}
    raw = p.read_text(encoding="utf-8")
    if not is_structured_document(raw):
        return {"ok": False, "error": "Yapılandırılmamış belge"}
    doc = parse_document(raw)
    body = doc.body_text()
    refs = extract_fn_refs(body)
    defined = {fn.num for fn in doc.footnotes}
    warnings: list[str] = []
    missing = sorted(refs - defined, key=int)
    unreferenced = sorted(defined - refs, key=int)
    if missing:
        warnings.append(f"Tanımsız dipnot göndermesi: {missing}")
    if unreferenced:
        warnings.append(f"Metinde geçmeyen dipnot tanımı: {unreferenced}")
    # Sıra denetimi: ilk geçiş sırası numaralamayla aynı olmalı.
    order = []
    for m in re.finditer(r"\[fn\s+(\d+)\]", body):
        if m.group(1) not in order:
            order.append(m.group(1))
    if order != sorted(order, key=int):
        warnings.append(f"Dipnot sırası bozuk (ilk geçiş): {order}")
    # Tekrar atıflar: aynı kaynağa 2+ gönderme (kısaltma adayı).
    counts: dict[str, int] = {}
    for m in re.finditer(r"\[fn\s+(\d+)\]", body):
        counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    repeated = {k: v for k, v in counts.items() if v > 1}
    return {"ok": True, "file": p.name, "refs": len(refs),
            "defined": len(defined), "warnings": warnings,
            "repeated_refs": repeated}


def bibliography(tr_path: Path | str, output_path: Path | str | None = None) -> dict:
    """Dipnotlardan tekilleştirilmiş kaynakça listesi üretir."""
    p = Path(tr_path)
    if not p.exists():
        return {"ok": False, "error": f"Dosya yok: {p}"}
    raw = p.read_text(encoding="utf-8")
    if not is_structured_document(raw):
        return {"ok": False, "error": "Yapılandırılmamış belge"}
    doc = parse_document(raw)
    seen: dict[str, str] = {}
    for fn in doc.footnotes:
        key = re.sub(r"\s+", " ", fn.text).strip().rstrip(".")
        short = _SHORT_TITLE_RE.match(key)
        norm = (short.group(1) if short else key[:60]).lower()
        seen.setdefault(norm, fn.text.strip())
    entries = sorted(seen.values(), key=str.lower)
    lines = ["[KAYNAKÇA]", ""]
    for i, entry in enumerate(entries, 1):
        lines.append(f"{i}. {entry}")
    out = Path(output_path) if output_path else p.with_name(p.stem + "_kaynakca.txt")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "source": p.name, "output": str(out),
            "footnotes": len(doc.footnotes), "entries": len(entries)}
