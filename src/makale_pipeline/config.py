"""Config cascade yükleyici: belge klasöründen proje köküne kadar birleştirir."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from makale_pipeline import DOCUMENTS_DIR

DEFAULT_DOCX: dict[str, Any] = {
    "page": "A4",
    "margin_cm": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5},
    "body_font": "Times New Roman",
    "body_size_pt": 12,
    "body_alignment": "justify",
    "line_spacing": 1.5,
    "space_after_pt": 6,
    "first_line_indent_cm": 1.25,
    "title_size_pt": 16,
    "subtitle_size_pt": 12,
    "heading1_size_pt": 14,
    "heading2_size_pt": 12,
    "footnote_size_pt": 10,
    "page_numbers": True,
    "page_number_position": "bottom_center",
    # İçindekiler: "auto" (kaynakta varsa) | true (zorla) | false (kapalı)
    "toc": "auto",
    "toc_title": "İçindekiler",
    # Dipnot kipi: "auto" (taslakta ne varsa) | "on" (isteniyor) | "off" (dipnotsuz)
    "footnotes": "auto",
    # Üstbilgi yedeği: [AUTHOR]/[INSTITUTION] bloğu yoksa kullanılır.
    "author": "",
    "institution": "",
}

DEFAULT_CONFIG: dict[str, Any] = {
    "document_name": "Untitled Document",
    "style": "academic",
    "source_lang": "en",
    "target_lang": "tr",
    "glossary": {},
    "prompt_override": "",
    "numbered_paragraphs": False,
    "source_layout_extraction": False,
    "expected_paragraphs": None,
    "expected_footnotes": None,
    # Derleme çıktıları: ["docx"] varsayılan; HTML için ["docx", "html"].
    "output_formats": ["docx"],
    # Word makale biçimi (aşağıdaki anahtarlar belge config.json ile ezilebilir).
    "docx": dict(DEFAULT_DOCX),
}

SCHEMA: dict[str, type | tuple[type, ...]] = {
    "document_name": str,
    "style": str,
    "source_lang": str,
    "target_lang": str,
    "glossary": dict,
    "prompt_override": str,
    "numbered_paragraphs": bool,
    "source_layout_extraction": bool,
    "expected_paragraphs": int,
    "expected_footnotes": int,
    "output_formats": list,
    "docx": dict,
}


def _deep_merge_glossary(base: dict, override: dict) -> dict:
    merged = dict(base or {})
    merged.update(override or {})
    return merged


def _deep_merge_docx(base: dict, override: dict) -> dict:
    merged = dict(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def load_config(doc_dir: Path, docs_root: Path | None = None) -> dict[str, Any]:
    """doc_dir'den documents köküne kadar config.json zincirini birleştirir.

    Alt klasördeki değerler üsttekileri ezer; glossary ve docx sözlükleri
    derin birleşir.
    """
    doc_dir = Path(doc_dir)
    cfg = dict(DEFAULT_CONFIG)
    cfg["docx"] = dict(DEFAULT_DOCX)
    if docs_root is None:
        docs_root = DOCUMENTS_DIR
    if not docs_root.is_dir():
        docs_root = doc_dir.parent

    chain: list[Path] = []
    current = doc_dir.resolve()
    while current != docs_root.resolve() and docs_root.resolve() in current.parents:
        chain.append(current)
        current = current.parent
    chain.append(docs_root.resolve())
    chain.reverse()

    for folder in chain:
        path = folder / "config.json"
        if not path.exists():
            continue
        try:
            with open(path, encoding="utf-8") as f:
                partial = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[config] {path}: {e}")
            continue
        glossary = partial.pop("glossary", None)
        docx = partial.pop("docx", None)
        cfg.update({k: v for k, v in partial.items() if v is not None})
        if glossary:
            cfg["glossary"] = _deep_merge_glossary(cfg.get("glossary", {}), glossary)
        if docx:
            cfg["docx"] = _deep_merge_docx(cfg.get("docx", {}), docx)

    return cfg


def validate_config_dict(data: dict) -> list[str]:
    """Bir config.json içeriğini şema açısından doğrular, uyarıları döndürür."""
    warnings: list[str] = []

    if not isinstance(data, dict):
        return ["config.json bir JSON nesnesi (obje) olmalı"]

    for key, value in data.items():
        if key not in SCHEMA:
            warnings.append(f"Bilinmeyen alan: '{key}' (yazım hatası olabilir)")
            continue
        expected = SCHEMA[key]
        if value is not None and not isinstance(value, expected):
            expected_name = getattr(expected, "__name__", str(expected))
            warnings.append(
                f"'{key}' alanı {expected_name} olmalı, {type(value).__name__} bulundu"
            )

    glossary = data.get("glossary")
    if isinstance(glossary, dict):
        for en_term, tr_term in glossary.items():
            if not isinstance(en_term, str) or not en_term.strip():
                warnings.append(f"Sözlükte geçersiz terim anahtarı: {en_term!r}")
            if not isinstance(tr_term, str) or not tr_term.strip():
                warnings.append(
                    f"Sözlükte boş/geçersiz karşılık: '{en_term}' -> {tr_term!r}"
                )

    return warnings


def validate_config_file(config_path: Path) -> list[str]:
    try:
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Geçersiz JSON: {e}"]
    except OSError as e:
        return [f"Dosya okunamadı: {e}"]
    return validate_config_dict(data)


def scan_configs(docs_dir: Path | None = None) -> dict[str, list[str]]:
    """documents altındaki tüm config.json dosyalarını doğrular."""
    docs_dir = docs_dir or DOCUMENTS_DIR
    results: dict[str, list[str]] = {}
    if not docs_dir.is_dir():
        return results
    for config_path in sorted(docs_dir.rglob("config.json")):
        rel = config_path.relative_to(docs_dir)
        results[str(rel)] = validate_config_file(config_path)
    return results
