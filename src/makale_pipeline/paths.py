"""Yol yardımcıları: kaynak/hedef eşleşmesi, dil sezme, kök-göreli çözümleme."""

from __future__ import annotations

import re
from pathlib import Path

LANG_SUFFIX_RE = re.compile(r"_([a-z]{2})$", re.IGNORECASE)

KNOWN_LANGS = {
    "tr", "en", "ar", "fr", "de", "ru", "it", "es", "fa", "ku", "ota",
}

DRAFT_SUFFIXES = ("_draft", "_ham", "_raw")


def infer_lang(file_name: str) -> str | None:
    """Dosya adındaki _xx son ekinden dili tahmin eder (ör. belge_en.txt)."""
    stem = Path(file_name).stem
    m = LANG_SUFFIX_RE.search(stem)
    if m and m.group(1).lower() in KNOWN_LANGS:
        return m.group(1).lower()
    return None


def _is_draft(name: str) -> bool:
    stem = Path(name).stem.lower()
    return any(stem.endswith(s) for s in DRAFT_SUFFIXES)


def find_source_files(doc_dir: Path) -> list[Path]:
    """Klasördeki kaynak metinleri listeler (hedef *_tr.txt ve taslaklar hariç)."""
    doc_dir = Path(doc_dir)
    if not doc_dir.is_dir():
        return []
    out: list[Path] = []
    for cand in sorted(doc_dir.glob("*.txt")):
        stem = cand.stem
        if stem.endswith("_tr") or _is_draft(cand.name):
            continue
        if cand.name.startswith("."):
            continue
        out.append(cand)
    return out


def target_path_for_source(source_path: Path) -> Path:
    """Kaynak dosya için hedef yolu üretir: <kök>_xx.txt -> <kök>_tr.txt."""
    src = Path(source_path)
    stem = src.stem
    m = LANG_SUFFIX_RE.search(stem)
    if m:
        base = stem[: m.start()]
    else:
        base = stem
    return src.with_name(f"{base}_tr.txt")


def resolve_path(root: Path, given: str | Path | None) -> Path | None:
    """Verilen yolu mutlaksa aynen, göreceyse proje köküne göre çözer."""
    if given is None:
        return None
    p = Path(given)
    if p.is_absolute():
        return p
    return Path(root) / p
