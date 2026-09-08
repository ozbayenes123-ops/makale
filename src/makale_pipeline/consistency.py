"""Sözlük (glossary) tutarlılığı: tanım ve uygulama denetimi."""

from __future__ import annotations

import re
from pathlib import Path

from makale_pipeline.config import load_config
from makale_pipeline.paths import target_path_for_source
from makale_pipeline.structured import is_structured_document, parse_document
from makale_pipeline.translation_qa import check_glossary_coverage


def show_glossary(source_path: Path) -> dict:
    """Kaynağın klasör zincirindeki sözlüğü ve kullanım özetini döndürür."""
    src = Path(source_path)
    config = load_config(src.parent)
    glossary = config.get("glossary", {}) or {}
    summary = []
    text = ""
    if src.exists():
        text = src.read_text(encoding="utf-8")
    tr = target_path_for_source(src)
    tr_text = tr.read_text(encoding="utf-8") if tr.exists() else ""
    for en_term, tr_term in sorted(glossary.items()):
        en_hit = bool(re.search(r"(?<!\w)" + re.escape(str(en_term)) + r"(?!\w)", text, re.IGNORECASE)) if text else False
        tr_hit = bool(re.search(r"(?<!\w)" + re.escape(str(tr_term)) + r"(?!\w)", tr_text, re.IGNORECASE)) if tr_text else False
        summary.append({
            "term": en_term, "gloss": tr_term,
            "in_source": en_hit, "in_target": tr_hit,
        })
    return {"terms": len(glossary), "entries": summary}


def check_glossary(source_path: Path) -> list[str]:
    """Sözlük uygulaması + hedefte çoklu karşılık varyantı denetimi."""
    src = Path(source_path)
    if not src.exists():
        return [f"Kaynak yok: {src}"]
    config = load_config(src.parent)
    glossary = config.get("glossary", {}) or {}
    if not glossary:
        return ["Sözlük tanımlı değil (glossary boş)"]
    tr = target_path_for_source(src)
    if not tr.exists():
        return [f"Hedef yok: {tr.name} — çeviri üretilince denetlenecek"]
    try:
        source = parse_document(src.read_text(encoding="utf-8"))
        target = parse_document(tr.read_text(encoding="utf-8"))
    except OSError as exc:
        return [f"Okuma hatası: {exc}"]
    if not is_structured_document(src.read_text(encoding="utf-8")):
        return ["Kaynak yapılandırılmamış"]
    return check_glossary_coverage(source, target, glossary)
