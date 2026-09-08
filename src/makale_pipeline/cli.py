"""makale komut satırı: durum, prompt, doğrulama, derleme, arama, MCP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from makale_pipeline import DOCUMENTS_DIR, PROJECT_ROOT, __version__


def _cmd_status(args) -> int:
    from makale_pipeline.translator import document_status

    st = document_status()
    print(f"Belgeler: {len(st['documents'])} | Bekleyen çeviri: {st['pending_translations']}")
    for row in st["documents"]:
        print(
            f"- {row['path']}/{row['source']} "
            f"[yapı:{'✓' if row['structured'] else '·'} "
            f"çeviri:{'✓' if row['translated'] else '·'} "
            f"docx:{'✓' if row.get('docx') else '·'}]"
        )
    return 0


def _cmd_prep(args) -> int:
    from makale_pipeline.translator import build_prompt

    print(build_prompt(Path(args.source)))
    return 0


def _cmd_apply(args) -> int:
    from makale_pipeline.translator import apply_translation

    res = apply_translation(Path(args.source))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res.get("ok") else 1


def _cmd_validate(args) -> int:
    from makale_pipeline.paths import target_path_for_source
    from makale_pipeline.validate import scan_all_documents, validate_pair

    if args.source:
        src = Path(args.source)
        warnings = validate_pair(src, target_path_for_source(src))
        print(json.dumps({src.name: warnings}, ensure_ascii=False, indent=1))
        return 0 if not warnings else 1
    results = scan_all_documents()
    bad = {k: v for k, v in results.items() if v}
    print(json.dumps(bad, ensure_ascii=False, indent=1))
    print(f"{len(results)} çift tarandı, {len(bad)} uyarılı.")
    return 0 if not bad else 1


def _cmd_compile(args) -> int:
    from makale_pipeline.pipeline import compile_all

    res = compile_all(force=args.force, parallel=not args.no_parallel)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if not res["errors"] else 1


def _cmd_index(args) -> int:
    from makale_pipeline.indexbuild import build_index

    print(json.dumps(build_index(), ensure_ascii=False))
    return 0


def _cmd_search(args) -> int:
    from makale_pipeline.search import search

    for hit in search(args.query, limit=args.limit, rebuild=args.rebuild):
        print(f"[{hit['file']}] {hit['snippet']}")
    return 0


def _cmd_quality(args) -> int:
    from makale_pipeline.quality import scan_all, scan_file

    if args.path:
        issues = scan_file(Path(args.path))
        print(json.dumps(issues, ensure_ascii=False, indent=1))
        return 0
    results = scan_all()
    total = sum(len(v) for v in results.values())
    print(f"{len(results)} dosya, {total} işaret.")
    for k, v in results.items():
        if v:
            print(f"## {k} ({len(v)})")
            for i in v[:10]:
                print(f"  - [{i['severity']}] {i['message']}")
    return 0


def _cmd_glossary(args) -> int:
    from makale_pipeline.consistency import check_glossary, show_glossary

    if args.show:
        print(json.dumps(show_glossary(Path(args.show)), ensure_ascii=False, indent=1))
        return 0
    warnings = check_glossary(Path(args.check))
    print(json.dumps(warnings, ensure_ascii=False, indent=1))
    return 0 if not warnings else 1


def _cmd_stats(args) -> int:
    from makale_pipeline.stats import project_stats

    print(json.dumps(project_stats(), ensure_ascii=False, indent=1))
    return 0


def _cmd_docs(args) -> int:
    from makale_pipeline.pipeline import list_compiled

    for rel in list_compiled():
        print(rel)
    return 0


def _cmd_semantic(args) -> int:
    from makale_pipeline.semantics import semantic_report, semantic_summary

    rep = semantic_report(Path(args.source))
    if args.summary:
        print(semantic_summary(rep))
    else:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0 if rep.get("ok") else 1


def _cmd_serve(args) -> int:
    from makale_pipeline.mcp_server import run_stdio

    run_stdio()
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="makale", description="Akademik makale çeviri ve derleme sistemi")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Belge durum tablosu")
    p = sub.add_parser("prep", help="Çeviri promptu üret")
    p.add_argument("source", help="Kaynak dosya yolu")
    p = sub.add_parser("apply", help="Çeviriyi doğrula + Word derle")
    p.add_argument("source", help="Kaynak dosya yolu")
    p = sub.add_parser("validate", help="Kaynak/hedef doğrulama")
    p.add_argument("source", nargs="?", default=None)
    p = sub.add_parser("compile", help="Tüm çevirileri derle (Word öncelikli)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-parallel", action="store_true")
    sub.add_parser("index", help="Ana kütüphane indeksini üret")
    p = sub.add_parser("search", help="Çevirilerde tam metin arama")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--rebuild", action="store_true")
    p = sub.add_parser("quality", help="Kalite taraması")
    p.add_argument("path", nargs="?", default=None)
    p = sub.add_parser("glossary", help="Glossary göster/tutarlılık")
    p.add_argument("--show", default=None)
    p.add_argument("--check", default=None)
    sub.add_parser("stats", help="Proje istatistikleri")
    sub.add_parser("docs", help="Derlenmiş belgeleri listele")
    p = sub.add_parser("semantic", help="Semantik bütünlük kontrolü (veri korunumu + cümle kalitesi)")
    p.add_argument("source")
    p.add_argument("--summary", action="store_true")
    sub.add_parser("serve", help="MCP sunucusunu stdio üzerinden çalıştır")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handlers = {
        "status": _cmd_status, "prep": _cmd_prep, "apply": _cmd_apply,
        "validate": _cmd_validate, "compile": _cmd_compile, "index": _cmd_index,
        "search": _cmd_search, "quality": _cmd_quality, "glossary": _cmd_glossary,
        "stats": _cmd_stats, "docs": _cmd_docs, "semantic": _cmd_semantic,
        "serve": _cmd_serve,
    }
    try:
        return handlers[args.command](args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Hata: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
