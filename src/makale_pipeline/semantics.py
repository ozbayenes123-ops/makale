"""Semantik bütünlük raporu: kaynak→hedef veri korunumu + cümle kalitesi.

Rapor bölümleri:
- numbers: sayı dizisi korunumu (adetli karşılaştırma)
- proper_nouns: kısaltma ve sık özel ad adayları
- glossary: sözlük kapsaması
- sentences: uzun/kısa cümle ve genel akış sinyalleri
"""

from __future__ import annotations

import re
from pathlib import Path

from makale_pipeline.config import load_config
from makale_pipeline.paths import target_path_for_source
from makale_pipeline.quality import scan_text
from makale_pipeline.structured import is_structured_document, parse_document
from makale_pipeline.translation_qa import (
    _acronyms,
    _digit_runs,
    check_glossary_coverage,
    check_numeric_coverage,
    check_proper_noun_coverage,
)


def _sentence_stats(text: str) -> dict:
    chunks = [c.strip() for c in re.split(r"[.!?]+", text) if c.strip()]
    lengths = [len(c.split()) for c in chunks]
    if not lengths:
        return {"sentences": 0, "avg_words": 0, "longest": 0}
    return {
        "sentences": len(lengths),
        "avg_words": round(sum(lengths) / len(lengths), 1),
        "longest": max(lengths),
    }


def semantic_report(source_path: Path) -> dict:
    """Kaynak/hedef çifti için semantik bütünlük raporu üretir."""
    src = Path(source_path)
    if not src.exists():
        return {"ok": False, "error": f"Kaynak yok: {src}"}
    tr = target_path_for_source(src)
    if not tr.exists():
        return {"ok": False, "error": f"Hedef yok: {tr.name}"}
    try:
        src_raw = src.read_text(encoding="utf-8")
        tr_raw = tr.read_text(encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "error": f"Okuma hatası: {exc}"}
    if not is_structured_document(src_raw) or not is_structured_document(tr_raw):
        return {"ok": False, "error": "Kaynak veya hedef yapılandırılmamış"}

    source = parse_document(src_raw)
    target = parse_document(tr_raw)
    config = load_config(src.parent)
    glossary = config.get("glossary", {}) or {}

    src_nums = _digit_runs(source.body_text())
    tr_nums = _digit_runs(target.body_text())
    numbers = {
        "source_unique": len(src_nums),
        "target_unique": len(tr_nums),
        "missing": sorted((src_nums - tr_nums).elements())[:10],
    }
    src_acr = _acronyms(source.body_text())
    tr_acr = _acronyms(target.body_text())
    proper_nouns = {
        "source_acronyms": sorted(src_acr.elements()),
        "missing_acronyms": sorted((src_acr - tr_acr).elements())[:10],
    }
    glossary_warnings = check_glossary_coverage(source, target, glossary)
    qa_warnings = (
        check_numeric_coverage(source, target)
        + check_proper_noun_coverage(source, target, glossary)
        + glossary_warnings
    )
    quality_flags = [
        i for i in scan_text(tr_raw)
        if i["type"] in ("yasakli_ifade", "uzun_cumle")
    ][:10]

    return {
        "ok": True,
        "source": src.name,
        "target": tr.name,
        "numbers": numbers,
        "proper_nouns": proper_nouns,
        "glossary_terms": len(glossary),
        "glossary_warnings": glossary_warnings,
        "qa_warnings": qa_warnings,
        "target_sentence_stats": _sentence_stats(target.body_text()),
        "quality_flags": quality_flags,
    }


def semantic_summary(report: dict) -> str:
    """Raporu tek paragraflık Türkçe özet cümleye indirir."""
    if not report.get("ok"):
        return f"Rapor üretilemedi: {report.get('error', 'bilinmeyen hata')}"
    nums = report["numbers"]
    nouns = report["proper_nouns"]
    bits = [
        f"{report['source']} -> {report['target']}",
        f"sayı: kaynakta {nums['source_unique']} çeşit, eksik {len(nums['missing'])}",
        f"kısaltma eksik {len(nouns['missing_acronyms'])}",
        f"sözlük uyarısı {len(report['glossary_warnings'])}",
        f"kalite işareti {len(report['quality_flags'])}",
    ]
    return "; ".join(bits) + "."
