"""makale MCP sunucusu: çeviri hattının tüm adımları AI asistanına tool olarak."""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from makale_pipeline import DOCUMENTS_DIR, PROJECT_ROOT

server = MCPServer("makale")


def _ok(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _err(exc: Exception) -> str:
    return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)


@server.tool(name="doc_status", title="Belge Durumu",
             description="Tüm belgelerin durum tablosu (yapı/çeviri/docx).")
async def tool_doc_status() -> str:
    try:
        from makale_pipeline.translator import document_status

        return _ok(document_status())
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(name="ocr_health", title="OCR Durumu",
             description="OCR backend durumunu bildirir (varsayılan yerel).")
async def tool_ocr_health(backend: str = "local") -> str:
    try:
        from makale_pipeline.ocr_client import health

        return _ok(health(backend))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(name="ocr_document", title="Belgeyi OCR'la",
             description="Taranmış PDF/görüntüyü yerel OCR ile metne döker, taslak yazar.")
async def tool_ocr_document(
    source_path: str,
    backend: str = "local",
    output_path: str | None = None,
) -> str:
    try:
        from makale_pipeline.ocr_client import ocr_document
        from makale_pipeline.paths import resolve_path

        src = resolve_path(PROJECT_ROOT, source_path)
        out = resolve_path(PROJECT_ROOT, output_path) if output_path else None
        return _ok(ocr_document(src, backend=backend, output_path=out))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(name="translate_prep", title="Çeviri Promptu",
             description="Kaynak için AI çeviri promptu üretir (anlam-öncelikli protokol + öz denetim).")
async def tool_translate_prep(source_path: str) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.translator import build_prompt

        return build_prompt(resolve_path(PROJECT_ROOT, source_path))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="translate_apply",
    title="Çeviriyi Uygula",
    description=(
        "AI'nın ürettiği _tr.txt dosyasını doğrular (paragraf/dipnot/sayı/"
        "sözlük kapsaması) ve makale formatında Word (.docx) derler."
    ),
)
async def tool_translate_apply(source_path: str) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.translator import apply_translation

        return _ok(apply_translation(resolve_path(PROJECT_ROOT, source_path)))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(name="write_translation", title="Çeviri Yaz",
             description="Çevrilmiş metni hedef _tr.txt dosyasına yazar (üzerine yazar).")
async def tool_write_translation(source_path: str, content: str) -> str:
    try:
        from makale_pipeline.paths import resolve_path, target_path_for_source

        src = resolve_path(PROJECT_ROOT, source_path)
        target = target_path_for_source(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return _ok({"ok": True, "target": str(target), "chars": len(content)})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="validate_document",
    title="Belge Doğrula",
    description="Bir kaynak/hedef çiftini doğrular; uyarı listesini JSON döndürür.",
)
async def tool_validate_document(source_path: str) -> str:
    try:
        from makale_pipeline.paths import resolve_path, target_path_for_source
        from makale_pipeline.validate import validate_pair

        src = resolve_path(PROJECT_ROOT, source_path)
        return _ok({"warnings": validate_pair(src, target_path_for_source(src))})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="validate_all",
    title="Tümünü Doğrula",
    description="Tüm config.json şemalarını ve kaynak/hedef çiftlerini doğrular; sorun raporu döndürür.",
)
async def tool_validate_all() -> str:
    try:
        from makale_pipeline.validate import validate_all

        return _ok(validate_all())
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(name="compile_all", title="Tümünü Derle",
             description="Tüm çevirileri derler (Word öncelikli, HTML config'e bağlı).")
async def tool_compile_all(force: bool = False, parallel: bool = True) -> str:
    try:
        from makale_pipeline.pipeline import compile_all

        return _ok(compile_all(force=force, parallel=parallel))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(name="compile_document", title="Belge Derle",
             description="Tek çeviriyi derler (Word öncelikli).")
async def tool_compile_document(translation_path: str, force: bool = True) -> str:
    try:
        from makale_pipeline.pipeline import compile_one
        from makale_pipeline.paths import resolve_path

        tr = resolve_path(PROJECT_ROOT, translation_path)
        return _ok(compile_one(tr, force))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(name="build_index", title="İndeks Kur",
             description="Kütüphane tam metin indeksini (index.json) üretir.")
async def tool_build_index() -> str:
    try:
        from makale_pipeline.indexbuild import build_index

        return _ok(build_index())
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(name="search", title="Ara",
             description="Çevirilerde tam metin arama; alıntılı sonuçlar döndürür.")
async def tool_search(query: str, rebuild: bool = False, limit: int = 0) -> str:
    try:
        from makale_pipeline.search import search

        return _ok({"hits": search(query, limit=limit or 20, rebuild=rebuild)})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(name="quality_scan", title="Kalite Tara",
             description="Çeviride yasaklı kalıp/uzun cümle/bağlaç tekrarı tarar.")
async def tool_quality_scan(path: str | None = None) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.quality import scan_all, scan_file

        if path:
            return _ok({"issues": scan_file(resolve_path(PROJECT_ROOT, path))})
        return _ok(scan_all())
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(name="glossary_check", title="Sözlük Denetle",
             description="Sözlük karşılıklarının hedefte uygulanıp uygulanmadığını denetler.")
async def tool_glossary_check(path: str | None = None) -> str:
    try:
        from makale_pipeline.consistency import check_glossary
        from makale_pipeline.paths import resolve_path

        if not path:
            return _ok({"warnings": ["Kaynak yolu verilmedi"]})
        return _ok({"warnings": check_glossary(resolve_path(PROJECT_ROOT, path))})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="semantic_check",
    title="Semantik Bütünlük",
    description=(
        "Semantik bütünlük raporu: kaynak→hedef sayı/yüzde/yıl/özel isim korunumu "
        "+ cümle kalitesi."
    ),
)
async def tool_semantic_check(path: str | None = None, summary: bool = False) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.semantics import semantic_report, semantic_summary

        if not path:
            return _ok({"ok": False, "error": "Kaynak yolu verilmedi"})
        rep = semantic_report(resolve_path(PROJECT_ROOT, path))
        if summary:
            return semantic_summary(rep)
        return _ok(rep)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(name="project_stats", title="Proje İstatistikleri",
             description="Belge/çeviri/paragraf/dipnot sayımları.")
async def tool_project_stats() -> str:
    try:
        from makale_pipeline.stats import project_stats

        return _ok(project_stats())
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(name="read_document", title="Belge Oku",
             description="Belge dosyasının ham metnini döndürür (inceleme için).")
async def tool_read_document(path: str) -> str:
    try:
        from makale_pipeline.paths import resolve_path

        fp = resolve_path(PROJECT_ROOT, path)
        return fp.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="extract_pdf",
    title="PDF Çıkar",
    description=(
        "Dijital PDF'ten metin çıkarıp ham [BODY]/p<n>: taslağını dosyaya yazar. "
        "output_path verilmezse kaynak yanına <ad>.draft.txt yazılır."
    ),
)
async def tool_extract_pdf(source_path: str, output_path: str | None = None) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.pdf_io import extract_pdf

        src = resolve_path(PROJECT_ROOT, source_path)
        out = resolve_path(PROJECT_ROOT, output_path) if output_path else None
        result = extract_pdf(src, out if out else src.with_suffix(".draft.txt"))
        return _ok(result)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="read_docx",
    title="DOCX Oku",
    description=(
        "Word belgesini paragraf stillerine göre yapılandırılmış taslağa döker "
        "([TITLE]/[SECTION]/p<n>/[FOOTNOTES]); dipnotları footnotes.xml'den çeker. "
        "output_path verilmezse kaynak yanına <ad>.draft.txt yazılır."
    ),
)
async def tool_read_docx(source_path: str, output_path: str | None = None) -> str:
    try:
        from makale_pipeline.docx_io import read_docx
        from makale_pipeline.paths import resolve_path

        src = resolve_path(PROJECT_ROOT, source_path)
        out = resolve_path(PROJECT_ROOT, output_path) if output_path else None
        result = read_docx(src, out)
        return _ok(result)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="export_docx",
    title="Word'e Aktar",
    description=(
        "Yapılandırılmış _tr.txt dosyasını makale formatında Word'e derler "
        "(A4, Times 12, 1.5 satır, gerçek dipnotlar, içindekiler, sayfa no). "
        "output_path verilmezse çevirinin yanına <ad>.docx yazılır."
    ),
)
async def tool_export_docx(translation_path: str, output_path: str | None = None) -> str:
    try:
        from makale_pipeline.article_docx import export_article_docx
        from makale_pipeline.config import load_config
        from makale_pipeline.paths import resolve_path

        tr = resolve_path(PROJECT_ROOT, translation_path)
        out = resolve_path(PROJECT_ROOT, output_path) if output_path else None
        cfg = load_config(tr.parent)
        result = export_article_docx(tr, out, style=cfg.get("docx", {}))
        return _ok(result)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="subtitle_read",
    title="Altyazı Oku",
    description=(
        "SRT dosyasını zaman damgalarını saklayarak ayrıştırır; AI'ya L<n>: "
        "numaralı metin listesi verir. map_path verilirse zaman haritası JSON "
        "olarak yazılır (subtitle_write bununla birleşir)."
    ),
)
async def tool_subtitle_read(source_path: str, map_path: str | None = None) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.subtitle_io import subtitle_read

        src = resolve_path(PROJECT_ROOT, source_path)
        mp = resolve_path(PROJECT_ROOT, map_path) if map_path else None
        return _ok(subtitle_read(src, mp))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="subtitle_write",
    title="Altyazı Yaz",
    description="Çevrilmiş L<n> satırları zaman haritasıyla birleştirip SRT yazar.",
)
async def tool_subtitle_write(
    source_path: str,
    map_path: str,
    lines: str,
    output_path: str | None = None,
) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.subtitle_io import subtitle_write

        src = resolve_path(PROJECT_ROOT, source_path)
        mp = resolve_path(PROJECT_ROOT, map_path)
        out = resolve_path(PROJECT_ROOT, output_path) if output_path else None
        return _ok(subtitle_write(src, mp, lines, out))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="fetch_article",
    title="Makaleyi Çek",
    description="URL'deki makaleyi çekip ham taslak dosyası yazar.",
)
async def tool_fetch_article(url: str, output_path: str | None = None) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.webfetch import fetch_article

        out = resolve_path(PROJECT_ROOT, output_path) if output_path else None
        if out is None:
            out = DOCUMENTS_DIR.parent / "incoming" / "fetched.draft.txt"
        return _ok(fetch_article(url, out))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="glossary_show",
    title="Sözlüğü Göster",
    description="Belgenin klasör zincirindeki sözlüğü ve kullanım özetini gösterir.",
)
async def tool_glossary_show(source_path: str) -> str:
    try:
        from makale_pipeline.consistency import show_glossary
        from makale_pipeline.paths import resolve_path

        return _ok(show_glossary(resolve_path(PROJECT_ROOT, source_path)))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.resource("makale://documents")
async def res_documents() -> str:
    """Belgeler klasörü listesi."""
    if not DOCUMENTS_DIR.is_dir():
        return "(belge yok)"
    return "\n".join(sorted(p.name for p in DOCUMENTS_DIR.iterdir()))


@server.resource("makale://index")
async def res_index() -> str:
    """Tam metin indeksi özeti."""
    from makale_pipeline.search import INDEX_FILE

    if not INDEX_FILE.exists():
        return "(indeks yok; build_index çalıştırın)"
    return INDEX_FILE.read_text(encoding="utf-8")[:4000]


@server.resource("makale://config/{relpath}")
async def res_config(relpath: str) -> str:
    """Belge config.json içeriği."""
    from makale_pipeline.paths import resolve_path

    fp = resolve_path(PROJECT_ROOT, relpath)
    return fp.read_text(encoding="utf-8")


@server.resource("makale://content/{relpath}")
async def res_content(relpath: str) -> str:
    """Belge ham içeriği (inceleme için, ilk 20000 karakter)."""
    from makale_pipeline.paths import resolve_path

    fp = resolve_path(PROJECT_ROOT, relpath)
    return fp.read_text(encoding="utf-8")[:20000]


@server.prompt()
async def prompt_translate_document(source_path: str) -> str:
    """Kaynak için çeviri promptu üretir."""
    from makale_pipeline.paths import resolve_path
    from makale_pipeline.translator import build_prompt

    return build_prompt(resolve_path(PROJECT_ROOT, source_path))


@server.prompt()
async def prompt_process_new_document() -> str:
    """Yeni belge işleme akışını anlatır (sınıflandırma->taslak->çeviri->derleme)."""
    return (
        "Yeni belge akışı:\n"
        "1. incoming/ klasörüne düşen dosyayı tanı ve sınıflandır (dil/tür).\n"
        "2. documents/<ad>/ klasörü aç; kaynağı [TITLE]/[BODY]/p<n> taslağına dök.\n"
        "3. translate_prep ile promptu al, çevir ve hedef _tr.txt dosyasını yaz.\n"
        "4. translate_apply ile doğrula ve Word (.docx) derle.\n"
        "5. validate_document + semantic_check ile son denetimi yap."
    )


@server.tool(
    name="translation_memory",
    title="Çeviri Belleği",
    description=(
        "Onaylı çeviri çiftlerini belleğe yazar (action=record) veya benzer "
        "kaynak için önceki karşılığı önerir (action=suggest, text gerekir)."
    ),
)
async def tool_translation_memory(
    action: str, source_path: str, text: str = ""
) -> str:
    try:
        from makale_pipeline import tmem
        from makale_pipeline.paths import resolve_path

        if action == "record":
            return _ok(tmem.record(resolve_path(PROJECT_ROOT, source_path)))
        if action == "suggest":
            doc_dir = resolve_path(PROJECT_ROOT, source_path)
            doc_dir = doc_dir if doc_dir.is_dir() else doc_dir.parent
            return _ok(tmem.suggest(doc_dir, text))
        return _ok({"ok": False, "error": f"Bilinmeyen action: {action}"})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="translate_diff",
    title="Çeviri Farkı",
    description="Kaynak/hedef paragrafları hizalar; eksik/fazla paragrafları listeler.",
)
async def tool_translate_diff(source_path: str) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.textdiff import para_diff

        return _ok(para_diff(resolve_path(PROJECT_ROOT, source_path)))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="compare_versions",
    title="Revizyon Karşılaştır",
    description="İki _tr revizyonu arasındaki paragraf farkını döndürür.",
)
async def tool_compare_versions(old_path: str, new_path: str) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.textdiff import compare_versions

        return _ok(compare_versions(
            resolve_path(PROJECT_ROOT, old_path),
            resolve_path(PROJECT_ROOT, new_path),
        ))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="chunk_translate",
    title="Parçalı Çeviri Promptu",
    description="Uzun belgeyi bölüm gruplarına bölüp her parça için prompt üretir.",
)
async def tool_chunk_translate(source_path: str, max_chars: int = 12000) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.textdiff import chunk_prompts

        res = chunk_prompts(resolve_path(PROJECT_ROOT, source_path), max_chars)
        if not res.get("ok"):
            return _ok(res)
        total = sum(len(p["prompt"]) for p in res["prompts"])
        return _ok({"ok": True, "parts": res["parts"],
                    "total_chars": total,
                    "prompts": res["prompts"]})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="glossary_extract",
    title="Terim Çıkar",
    description="Kaynaktan sözlük adayı terimleri sıklıkla çıkarır.",
)
async def tool_glossary_extract(source_path: str, top: int = 40) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.terminology import extract_candidates

        return _ok(extract_candidates(resolve_path(PROJECT_ROOT, source_path), top))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="glossary_add",
    title="Sözlüğe Ekle",
    description="Seçili terimleri belgenin config.json sözlüğüne ekler.",
)
async def tool_glossary_add(source_path: str, entries: dict) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.terminology import add_to_glossary

        return _ok(add_to_glossary(resolve_path(PROJECT_ROOT, source_path), entries))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="terminology_corpus",
    title="Külliyat Tutarlılığı",
    description="Tüm külliyatta sözlük terimlerinin belge bazında kapsama matrisi.",
)
async def tool_terminology_corpus() -> str:
    try:
        from makale_pipeline.terminology import corpus_consistency

        return _ok(corpus_consistency())
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="citation_check",
    title="Atıf Denetle",
    description="Dipnot gönderim/tanım eşleşmesi, sıra ve tekrar atıfları denetler.",
)
async def tool_citation_check(translation_path: str) -> str:
    try:
        from makale_pipeline.citations import citation_check
        from makale_pipeline.paths import resolve_path

        return _ok(citation_check(resolve_path(PROJECT_ROOT, translation_path)))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="bibliography",
    title="Kaynakça Üret",
    description="Dipnot listesinden tekilleştirilmiş kaynakça dosyası üretir.",
)
async def tool_bibliography(
    translation_path: str, output_path: str | None = None
) -> str:
    try:
        from makale_pipeline.citations import bibliography
        from makale_pipeline.paths import resolve_path

        tr = resolve_path(PROJECT_ROOT, translation_path)
        out = resolve_path(PROJECT_ROOT, output_path) if output_path else None
        return _ok(bibliography(tr, out))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="read_feedback",
    title="Geri Bildirimi Oku",
    description="Word'deki izlenen değişiklikleri ve yorumları raporlar.",
)
async def tool_read_feedback(docx_path: str) -> str:
    try:
        from makale_pipeline.feedback import read_feedback
        from makale_pipeline.paths import resolve_path

        return _ok(read_feedback(resolve_path(PROJECT_ROOT, docx_path)))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="quality_fix",
    title="Kalite Düzelt",
    description="Mekanik sorunları düzeltir; yasaklı kalıplara öneri üretir.",
)
async def tool_quality_fix(translation_path: str, apply_safe: bool = True) -> str:
    try:
        from makale_pipeline.fixer import fix_file
        from makale_pipeline.paths import resolve_path

        return _ok(fix_file(resolve_path(PROJECT_ROOT, translation_path), apply_safe))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@server.tool(
    name="export_pdf",
    title="PDF'e Aktar",
    description="Derlenmiş .docx dosyasını PDF'e çevirir (Word gerekir).",
)
async def tool_export_pdf(
    docx_path: str, output_path: str | None = None
) -> str:
    try:
        from makale_pipeline.paths import resolve_path
        from makale_pipeline.pdfexport import export_pdf

        src = resolve_path(PROJECT_ROOT, docx_path)
        out = resolve_path(PROJECT_ROOT, output_path) if output_path else None
        return _ok(export_pdf(src, out))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


def run_stdio() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    run_stdio()
