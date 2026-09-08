"""Paragraf hizalı fark: kaynak/hedef karşılaştırma, revizyon diff, parça prompt."""

from __future__ import annotations

import difflib
from pathlib import Path

from makale_pipeline.structured import is_structured_document, parse_document
from makale_pipeline.translation_qa import _align_paragraphs


def para_diff(source_path: Path | str) -> dict:
    """Kaynak/hedef paragrafları hizalar; eksik/fazla paragrafları işaretler."""
    from makale_pipeline.paths import target_path_for_source

    src = Path(source_path)
    tr = target_path_for_source(src)
    if not src.exists():
        return {"ok": False, "error": f"Kaynak yok: {src}"}
    if not tr.exists():
        return {"ok": False, "error": f"Hedef yok: {tr.name}"}
    src_raw, tr_raw = src.read_text(encoding="utf-8"), tr.read_text(encoding="utf-8")
    if not is_structured_document(src_raw) or not is_structured_document(tr_raw):
        return {"ok": False, "error": "Kaynak veya hedef yapılandırılmamış"}
    source = parse_document(src_raw)
    target = parse_document(tr_raw)
    src_paras = [(p.num, p.text) for s in source.sections for p in s.paragraphs]
    tr_paras = [(p.num, p.text) for s in target.sections for p in s.paragraphs]
    aligned = _align_paragraphs([t for _, t in src_paras], [t for _, t in tr_paras])
    used_tr = {j for _, j in aligned if j >= 0}
    rows = []
    for i, j in aligned:
        snum, stext = src_paras[i]
        if j < 0:
            rows.append({"src_n": snum, "tr_n": None, "status": "hedefte_yok",
                         "src": stext[:200], "tr": None})
        else:
            tnum, ttext = tr_paras[j]
            rows.append({"src_n": snum, "tr_n": tnum,
                         "status": "ok" if stext.strip() and ttext.strip() else "bos",
                         "src": stext[:200], "tr": ttext[:200]})
    for j, (tnum, ttext) in enumerate(tr_paras):
        if j not in used_tr:
            rows.append({"src_n": None, "tr_n": tnum, "status": "kaynakta_yok",
                         "src": None, "tr": ttext[:200]})
    missing = sum(1 for r in rows if r["status"] == "hedefte_yok")
    extra = sum(1 for r in rows if r["status"] == "kaynakta_yok")
    return {"ok": True, "source": src.name, "target": tr.name,
            "paragraphs": len(rows), "missing": missing, "extra": extra, "rows": rows}


def compare_versions(old_path: Path | str, new_path: Path | str) -> dict:
    """İki _tr revizyonu arasındaki paragraf farkını döndürür."""
    old = Path(old_path).read_text(encoding="utf-8").splitlines()
    new = Path(new_path).read_text(encoding="utf-8").splitlines()
    diff = list(difflib.unified_diff(old, new, lineterm="",
                                     fromfile=Path(old_path).name,
                                     tofile=Path(new_path).name))
    changed = [ln for ln in diff if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))]
    return {"ok": True, "changed_lines": len(changed),
            "diff": "\n".join(diff[:400])}


def chunk_prompts(source_path: Path | str, max_chars: int = 12000) -> dict:
    """Uzun belgeyi bölüm gruplarına bölüp her parça için çeviri promptu üretir."""
    from makale_pipeline.config import load_config
    from makale_pipeline.paths import infer_lang, target_path_for_source
    from makale_pipeline.structured import serialize_document
    from makale_pipeline.models import StructuredDocument
    from makale_pipeline.translator import (
        PROMPT_TEMPLATE, QA_CHECKLIST, SEMANTIC_PROTOCOL, _build_document_map,
    )
    from makale_pipeline import PROJECT_ROOT

    src = Path(source_path)
    raw = src.read_text(encoding="utf-8")
    if not is_structured_document(raw):
        return {"ok": False, "error": "Kaynak yapılandırılmamış"}
    doc = parse_document(raw)
    config = load_config(src.parent)
    glossary = config.get("glossary", {}) or {}
    gloss_block = ("Glossary (TUTARLI uygula):\n" + "\n".join(f"  - {k} -> {v}" for k, v in glossary.items())) if glossary else "Glossary: (tanımlı değil)"

    chunks: list[list] = [[]]
    sizes = [0]
    for sec in doc.sections:
        size = sum(len(p.text) for p in sec.paragraphs) + len(sec.title)
        if sizes[-1] + size > max_chars and chunks[-1]:
            chunks.append([])
            sizes.append(0)
        chunks[-1].append(sec)
        sizes[-1] += size

    target_rel = target_path_for_source(src).relative_to(PROJECT_ROOT)
    prompts = []
    for idx, secs in enumerate(chunks, 1):
        sub = StructuredDocument(title=doc.title, subtitle=doc.subtitle,
                                 vat_label=doc.vat_label, sections=secs,
                                 footnotes=doc.footnotes, is_structured=True)
        sub_text = serialize_document(sub)
        prompts.append({
            "part": f"{idx}/{len(chunks)}",
            "sections": [s.section_id for s in secs],
            "prompt": PROMPT_TEMPLATE.format(
                rel_path=f"{src.relative_to(PROJECT_ROOT)} [parça {idx}/{len(chunks)}]",
                target_rel=f"{target_rel} [parça {idx}/{len(chunks)} — AYNI dosyaya, ilgili bölüme yaz]",
                style=config.get("style", "academic"),
                source_lang=infer_lang(src.name) or config.get("source_lang", "en"),
                target_lang=config.get("target_lang", "tr"),
                document_map=_build_document_map(sub_text),
                semantic_protocol=SEMANTIC_PROTOCOL,
                source_text=sub_text,
                glossary_block=gloss_block,
                qa_checklist=QA_CHECKLIST,
            ),
        })
    return {"ok": True, "parts": len(prompts), "prompts": prompts}
