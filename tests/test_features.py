# -*- coding: utf-8 -*-
"""Yeni modüllerin testleri: fark, terminoloji, atıf, düzeltme, bellek, geri bildirim."""

from pathlib import Path

from makale_pipeline.article_docx import export_article_docx
from makale_pipeline.citations import bibliography, citation_check
from makale_pipeline.docx_io import read_docx
from makale_pipeline.feedback import read_feedback
from makale_pipeline.fixer import fix_file
from makale_pipeline.terminology import add_to_glossary, extract_candidates
from makale_pipeline.textdiff import compare_versions, para_diff
from makale_pipeline import tmem

SAMPLE = """[TITLE]
Başlık
[/TITLE]

[BODY]
[SECTION id="sec1" title="Giriş"]
p1: Ankara ve İstanbul şehirleri 1971 yılında UNESCO raporunda geçti [fn 1].
p2: İkinci paragraf burada biter.
[/SECTION]
[/BODY]

[FOOTNOTES]
1: Rapor dipnotu, s. 12.
[/FOOTNOTES]
"""


def _pair(tmp_path):
    src = tmp_path / "b_en.txt"
    src.write_text(SAMPLE, encoding="utf-8")
    tr = tmp_path / "b_tr.txt"
    tr.write_text(SAMPLE, encoding="utf-8")
    return src, tr


def test_para_diff_ok(tmp_path):
    src, _ = _pair(tmp_path)
    res = para_diff(src)
    assert res["ok"] is True
    assert res["missing"] == 0 and res["extra"] == 0


def test_para_diff_missing(tmp_path):
    src, tr = _pair(tmp_path)
    tr.write_text(SAMPLE.replace("p2: İkinci paragraf burada biter.\n", ""), encoding="utf-8")
    res = para_diff(src)
    assert res["missing"] == 1


def test_compare_versions(tmp_path):
    _, tr = _pair(tmp_path)
    v2 = tmp_path / "b_tr_v2.txt"
    v2.write_text(SAMPLE.replace("burada biter", "sona erer"), encoding="utf-8")
    res = compare_versions(tr, v2)
    assert res["ok"] is True and res["changed_lines"] > 0


def test_extract_candidates(tmp_path):
    src, _ = _pair(tmp_path)
    res = extract_candidates(src)
    assert res["ok"] is True
    terms = [c["term"] for c in res["candidates"]]
    assert "UNESCO" in terms


def test_add_to_glossary(tmp_path):
    src, _ = _pair(tmp_path)
    res = add_to_glossary(src, {"UNESCO": "UNESCO"})
    assert res["ok"] is True and res["added"] == ["UNESCO"]
    res2 = add_to_glossary(src, {"UNESCO": "UNESCO"})
    assert res2["added"] == []


def test_citation_check_ok(tmp_path):
    _, tr = _pair(tmp_path)
    rep = citation_check(tr)
    assert rep["ok"] is True and rep["warnings"] == []


def test_citation_check_missing(tmp_path):
    _, tr = _pair(tmp_path)
    tr.write_text(SAMPLE.replace("[FOOTNOTES]", "[BODY]").replace("1: Rapor", "9: Rapor"), encoding="utf-8")
    rep = citation_check(tr)
    assert rep["warnings"]


def test_bibliography(tmp_path):
    _, tr = _pair(tmp_path)
    res = bibliography(tr)
    assert res["ok"] is True and res["entries"] == 1
    assert Path(res["output"]).exists()


def test_fix_mechanical(tmp_path):
    f = tmp_path / "x_tr.txt"
    f.write_text("Merhaba  dünya.\n\n\n\nSon.", encoding="utf-8")
    res = fix_file(f)
    assert res["ok"] is True and res["changed"] is True
    assert "  " not in f.read_text(encoding="utf-8")


def test_fix_suggest(tmp_path):
    f = tmp_path / "y_tr.txt"
    f.write_text("Bu oldukça önemli bir husustur.", encoding="utf-8")
    res = fix_file(f)
    assert any(s["phrase"].lower() == "oldukça" for s in res["suggestions"])


def test_tmem_roundtrip(tmp_path):
    src, _ = _pair(tmp_path)
    rec = tmem.record(src)
    assert rec["ok"] is True and rec["added"] >= 1
    sug = tmem.suggest(tmp_path, "Ankara ve İstanbul şehirleri 1971 yılında raporda geçti.")
    assert sug["entries"] >= 1


def test_read_docx_roundtrip_keeps_fn(tmp_path):
    _, tr = _pair(tmp_path)
    info = export_article_docx(tr, tr.with_suffix(".docx"), style={})
    back = read_docx(info["output"])
    draft = Path(back["output"]).read_text(encoding="utf-8")
    assert "[fn 1]" in draft
    assert "Rapor dipnotu" in draft


def test_read_feedback_empty(tmp_path):
    _, tr = _pair(tmp_path)
    info = export_article_docx(tr, tr.with_suffix(".docx"), style={})
    rep = read_feedback(info["output"])
    assert rep["ok"] is True and rep["total"] == 0


def test_ustbilgi_isaretci_bicimleri():
    """Üstbilgi işaretçileri hem blok hem tek satır/kapanışsız biçimde okunmalı."""
    from makale_pipeline.structured import parse_document

    # tek satırlı blok + tırnaklı öznitelik + öznitelikli SECTION
    doc = parse_document(
        "[TITLE]Başlık[/TITLE]\n"
        '[SUBTITLE title=“Yazar, Dergi 1/2 (1995)”]\n'
        "[AUTHOR]Yazar Adı[/AUTHOR]\n"
        "[INSTITUTION]Kurum[/INSTITUTION]\n"
        "[BODY]\n"
        "[SECTION title=“Özet”]\n"
        "p1: metin\n"
    )
    assert doc.title == "Başlık"
    assert doc.subtitle == "Yazar, Dergi 1/2 (1995)"
    assert doc.author == "Yazar Adı"
    assert doc.institution == "Kurum"
    assert doc.sections[0].title == "Özet"

    # çok satırlı blok biçimi de çalışmalı
    doc2 = parse_document(
        "[TITLE]\nUzun Başlık\n[/TITLE]\n[BODY]\np1: metin\n"
    )
    assert doc2.title == "Uzun Başlık"


def test_ustbilgi_docx_e_yazilir(tmp_path):
    """Yazar/kurum/alt başlık derlenen DOCX'te görünmeli (eskiden kayboluyordu)."""
    import re
    import zipfile

    src = tmp_path / "makale_en.txt"
    src.write_text("[TITLE]English Title[/TITLE]\n[BODY]\np1: source\n", encoding="utf-8")
    tr = tmp_path / "makale_tr.txt"
    tr.write_text(
        "[TITLE]Türkçe Başlık[/TITLE]\n"
        "[SUBTITLE]Dergi 5/1 (2000), ss. 1-10[/SUBTITLE]\n"
        "[AUTHOR]Ayşe Yılmaz[/AUTHOR]\n"
        "[INSTITUTION]Örnek Üniversitesi[/INSTITUTION]\n"
        "[BODY]\np1: çeviri metni\n[/BODY]\n",
        encoding="utf-8",
    )
    info = export_article_docx(tr, tmp_path / "makale_tr.docx", style={})
    xml = zipfile.ZipFile(info["output"]).read("word/document.xml").decode()
    text = " ".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml))
    assert "Türkçe Başlık" in text
    assert "Ayşe Yılmaz" in text
    assert "Örnek Üniversitesi" in text
    assert "Dergi 5/1 (2000), ss. 1-10" in text
    assert "İçindekiler" not in text  # kaynakta TOC yok → uydurma içindekiler yok
