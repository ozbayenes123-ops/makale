"""Toplu derleme hattı: tüm çevirileri config çıktılarına derler."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from makale_pipeline import DOCUMENTS_DIR, PROJECT_ROOT, TEMPLATE_FILE
from makale_pipeline.article_docx import export_article_docx
from makale_pipeline.compile import compile_document
from makale_pipeline.config import load_config
from makale_pipeline.paths import find_source_files, target_path_for_source
from makale_pipeline.structured import is_structured_document


def _compile_one(tr: Path, force: bool) -> dict:
    config = load_config(tr.parent)
    formats = [str(f).lower() for f in (config.get("output_formats") or ["docx"])]
    made: list[str] = []
    errors: list[str] = []
    if "docx" in formats:
        out = tr.with_suffix(".docx")
        if force or not out.exists():
            try:
                export_article_docx(tr, out, style=config.get("docx", {}))
                made.append("docx")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"docx: {exc}")
    if "html" in formats:
        out = tr.with_suffix(".html")
        if force or not out.exists():
            if not TEMPLATE_FILE.exists():
                errors.append(f"html: şablon yok {TEMPLATE_FILE}")
            elif compile_document(tr, TEMPLATE_FILE, out):
                made.append("html")
            else:
                errors.append("html: derleme başarısız")
    return {"target": str(tr), "made": made, "errors": errors}


def compile_all(
    docs_dir: Path | None = None,
    force: bool = False,
    parallel: bool = True,
) -> dict:
    """Tüm *_tr.txt çevirilerini derler; özet dict döndürür."""
    docs_dir = Path(docs_dir or DOCUMENTS_DIR)
    targets: list[Path] = []
    if docs_dir.is_dir():
        for root, _, files in os.walk(docs_dir):
            p = Path(root)
            for src in find_source_files(p):
                tr = target_path_for_source(src)
                if tr.exists() and is_structured_document(
                    tr.read_text(encoding="utf-8")
                ):
                    targets.append(tr)
            for tr in p.glob("*_tr.txt"):
                if tr.name.endswith("_draft.txt") or tr in targets:
                    continue
                try:
                    if is_structured_document(tr.read_text(encoding="utf-8")):
                        targets.append(tr)
                except OSError:
                    continue

    results: list[dict] = []
    if parallel and len(targets) > 1:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda t: _compile_one(t, force), targets))
    else:
        results = [_compile_one(t, force) for t in targets]

    made = sum(len(r["made"]) for r in results)
    errors = [e for r in results for e in r["errors"]]
    return {
        "documents": len(targets),
        "artifacts": made,
        "errors": errors,
        "details": [
            {"target": r["target"], "made": r["made"]} for r in results if r["made"]
        ],
    }


def list_compiled(docs_dir: Path | None = None) -> list[str]:
    """Derlenmiş (.docx/.html) dosyaları proje köküne göreli listeler."""
    docs_dir = Path(docs_dir or DOCUMENTS_DIR)
    out: list[str] = []
    if docs_dir.is_dir():
        for ext in ("*.docx", "*.html"):
            for p in sorted(docs_dir.rglob(ext)):
                try:
                    out.append(str(p.relative_to(PROJECT_ROOT)))
                except ValueError:
                    out.append(str(p))
    return out
