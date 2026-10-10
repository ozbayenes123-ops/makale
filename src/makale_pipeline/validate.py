"""Çeviri doğrulama: kaynak–hedef eşleşmesi, dipnot, kalite, yapı."""

from __future__ import annotations

import os
import re
from pathlib import Path

from makale_pipeline import DOCUMENTS_DIR, PROJECT_ROOT
from makale_pipeline.config import load_config, scan_configs, validate_config_dict
from makale_pipeline.paths import (
    find_source_files,
    infer_lang,
    target_path_for_source,
)
from makale_pipeline.quality import scan_text
from makale_pipeline.structured import (
    byline_hint,
    extract_fn_refs,
    is_structured_document,
    parse_document,
    serialize_document,
)
from makale_pipeline.translation_qa import (
    check_glossary_coverage,
    check_numeric_coverage,
)

MIN_RATIO_BY_LANG = {
    "ar": 0.25,
    "fr": 0.30,
    "en": 0.35,
    "de": 0.35,
    "ru": 0.35,
}

LONG_SENTENCE_THRESHOLD = 40
SHORT_SENTENCE_THRESHOLD = 5

DIR_SUFFIX_RE = re.compile(r"\b\w+[dDtT][ıiİİ][rR]\b")

# Dipnot içi atıf kısaltmaları: kısa-cümle ve Arapça etkisi denetiminden muaftır.
CITATION_SENT_RE = re.compile(
    r"^\s*(s\.|ss\.|p\.|pp\.|c\.|bkz\.?|krş\.?|krş|ibid\.?|a\.g\.e\.?|a\.g\.m\.?|"
    r"çev\.?|haz\.?|ed\.?|yay\.?|no\.?|nr\.?|v\.|vv\.|md\.?)\b",
    re.IGNORECASE,
)


def _sentences_of(doc) -> list[tuple[str, bool]]:
    """(cümle, dipnot_mi) çiftleri: paragraf ve dipnot metinlerinden."""
    sentences: list[tuple[str, bool]] = []
    for chunk in [p.text for s in doc.sections for p in s.paragraphs]:
        for sent in re.split(r"[.!?]+", chunk):
            sentences.append((sent, False))
    for chunk in [fn.text for fn in doc.footnotes]:
        for sent in re.split(r"[.!?]+", chunk):
            sentences.append((sent, True))
    return sentences


def validate_pair(source_path: Path, target_path: Path) -> list[str]:
    """Bir kaynak/hedef çiftini doğrular, uyarı mesajlarını döndürür."""
    warnings: list[str] = []
    with open(source_path, encoding="utf-8") as f:
        src_raw = f.read()
    if not target_path.exists():
        return [f"Hedef dosya yok: {target_path.name}"]

    with open(target_path, encoding="utf-8") as f:
        tr_raw = f.read()

    if not is_structured_document(src_raw):
        warnings.append("Kaynak yapılandırılmamış ([BODY] yok)")
        return warnings
    if not is_structured_document(tr_raw):
        warnings.append("Hedef yapılandırılmamış ([BODY] yok)")
        return warnings

    source = parse_document(src_raw)
    target = parse_document(tr_raw)
    config = load_config(source_path.parent)
    source_is_layout_extraction = config.get("source_layout_extraction", False)

    sp = source.paragraph_count
    tp = target.paragraph_count
    if not source_is_layout_extraction and sp != tp:
        warnings.append(f"Paragraf sayısı: kaynak={sp}, hedef={tp}")

    expected_paragraphs = config.get("expected_paragraphs")
    if expected_paragraphs is not None and tp != expected_paragraphs:
        warnings.append(
            f"Hedef paragraf sayısı: hedef={tp}, beklenen={expected_paragraphs}"
        )

    src_text = serialize_document(source)
    tr_text = serialize_document(target)
    src_fns = extract_fn_refs(src_text)
    tr_fns = extract_fn_refs(tr_text)
    if not source_is_layout_extraction:
        missing = sorted(src_fns - tr_fns, key=int)
        extra = sorted(tr_fns - src_fns, key=int)
        if missing:
            warnings.append(f"Eksik dipnot atıfları: {missing}")
        if extra:
            warnings.append(f"Fazla dipnot atıfları: {extra}")

    expected_footnotes = config.get("expected_footnotes")
    if expected_footnotes is not None and target.footnote_count != expected_footnotes:
        warnings.append(
            f"Dipnot listesi: hedef={target.footnote_count}, beklenen={expected_footnotes}"
        )
    elif not source_is_layout_extraction and source.footnote_count != target.footnote_count:
        warnings.append(
            f"Dipnot listesi: kaynak={source.footnote_count}, hedef={target.footnote_count}"
        )

    # Yazar/kurum: kaynakta varsa ama hedefte yoksa raporla (değer uydurulmaz).
    if target.title and not (target.author or target.institution):
        if source.author or source.institution:
            warnings.append(
                "Hedefte [AUTHOR]/[INSTITUTION] yok ama kaynakta yazar/kurum "
                "bilgisi var — başlık altında yazar/kurum bloğu ekleyin."
            )
        elif byline_hint(src_raw):
            warnings.append(
                "Kaynağın ilk satırları yazar/kurum taşıyor gibi görünüyor ama "
                "hedefte [AUTHOR]/[INSTITUTION] yok — değerleri kaynaktan alıp ekleyin."
            )

    src_len = len(source.body_text())
    tr_len = len(target.body_text())
    lang = infer_lang(source_path.name)
    min_ratio = MIN_RATIO_BY_LANG.get(lang, 0.35)
    if src_len > 200 and tr_len < src_len * min_ratio:
        warnings.append(
            f"Hedef metin çok kısa (oran {tr_len / src_len:.0%}, eşik {min_ratio:.0%}); özetleme olabilir"
        )

    if "**" in tr_text:
        warnings.append("Hedefte ham markdown (**) kaldı — düzeltin veya yeniden derleyin")

    phrase_issues = scan_text(tr_raw)
    for iss in phrase_issues:
        if iss["type"] == "yasakli_ifade":
            warnings.append(f"Yasakli ifade: '{iss['message'].split(':')[-1].strip()}'")

    # Çeviri QA: sayı/veri ve sözlük kapsama kontrolleri
    for qa in check_numeric_coverage(source, target):
        warnings.append(qa)
    for qa in check_glossary_coverage(source, target, config.get("glossary", {})):
        warnings.append(qa)

    sentences = _sentences_of(target)
    for sent, is_footnote in sentences:
        words = sent.strip().split()
        if not words:
            continue
        if is_footnote and CITATION_SENT_RE.match(sent.strip()):
            continue  # dipnot atıf kısaltması (s. 42, bkz. vb.)
        first_word = words[0].lower()
        if any(first_word.startswith(p) for p in ("p", "fn", "http", "www", "krş", "bkz")):
            continue
        if re.match(r"^\[fn\s+\d+\]$", sent.strip()):
            continue
        if re.match(r"^[\d\.,;:\-\[\]()/]+$", sent.strip()):
            continue
        if len(words) > LONG_SENTENCE_THRESHOLD:
            preview = " ".join(words[:8])
            warnings.append(f"Uzun cumle ({len(words)} kelime): '{preview}...'")
        elif len(words) <= SHORT_SENTENCE_THRESHOLD:
            preview = " ".join(words)
            warnings.append(f"Kisa cumle ({len(words)} kelime): '{preview}'")

    dir_matches = DIR_SUFFIX_RE.findall(tr_text)
    total_sentences = max(len(sentences), 1)
    if dir_matches and len(dir_matches) / total_sentences > 0.6:
        warnings.append(
            f"-dir/-dir eki sik kullanilmis (cumle basina {len(dir_matches) / total_sentences:.1f}, {len(dir_matches)} kez)"
        )

    return warnings


def validate_directory(doc_dir: Path) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    for src in find_source_files(doc_dir):
        tr = target_path_for_source(src)
        key = f"{src.name} -> {tr.name}"
        results[key] = validate_pair(src, tr)
    return results


def scan_all_documents(docs_dir: Path | None = None) -> dict[str, list[str]]:
    docs_dir = docs_dir or DOCUMENTS_DIR
    all_results: dict[str, list[str]] = {}
    if not docs_dir.is_dir():
        return all_results
    for root, _, files in os.walk(docs_dir):
        p = Path(root)
        if p == docs_dir:
            continue
        if not any(f.endswith(".txt") for f in files):
            continue
        for src in find_source_files(p):
            tr = target_path_for_source(src)
            rel = p.relative_to(docs_dir)
            key = f"{rel}/{src.name}"
            all_results[key] = validate_pair(src, tr)
    return all_results


def validate_all(
    docs_dir: Path | None = None,
) -> dict[str, dict]:
    """Kapsamlı doğrulama: config şeması + kaynak/hedef çiftleri.

    Dönen yapı:
      {"configs": {rel_path: [uyarılar]}, "translations": {key: [uyarılar]}}
    """
    return {
        "configs": scan_configs(docs_dir),
        "translations": scan_all_documents(docs_dir),
    }


def config_issues(docs_dir: Path | None = None) -> dict[str, list[str]]:
    return scan_configs(docs_dir)
