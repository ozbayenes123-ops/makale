# -*- coding: utf-8 -*-
"""Talep güdümlü DOCX testleri: dipnot kipi, içindekiler varlığı, yazar/kurum.

Her test üretilen .docx'i unzip edip word/document.xml / word/footnotes.xml
içeriğini gerçekten denetler (varsayım değil, kanıt).
"""

import zipfile
from pathlib import Path

from makale_pipeline.article_docx import export_article_docx, resolve_footnote_mode
from makale_pipeline.config import DEFAULT_DOCX, load_config, validate_config_dict
from makale_pipeline.structured import (
    byline_hint,
    parse_document,
    serialize_document,
    source_contains_toc_heading,
)
from makale_pipeline.validate import validate_pair

# Dipnotlu + yazarlı taslak; İÇİNDEKİLER YOK.
DRAFT = """[TITLE]
Örnek Başlık
[/TITLE]
[AUTHOR]
Eray Alim
[/AUTHOR]
[INSTITUTION]
Ankara Üniversitesi, Siyaset Bilimi
[/INSTITUTION]
[BODY]
[SECTION id="sec1" title="Giriş"]
p1: İlk paragraf 1971 yılında geçen bir olayı anlatır [fn 1].
p2: İkinci paragraf [fn 2] dipnotuna değinir.
[/SECTION]
[/BODY]

[FOOTNOTES]
1: Dipnot metni burada.
2: İkinci dipnot metni.
3: Referanssız (metinde gönderme yok) dipnot.
[/FOOTNOTES]
"""

DRAFT_NO_FN = """[TITLE]
Dipnotsuz Başlık
[/TITLE]
[BODY]
p1: Dipnotsuz tek paragraf.
[/BODY]
"""


def _make_doc_dir(tmp_path, name="vaka"):
    d = tmp_path / name
    d.mkdir()
    # Kaynak dosya: TOC başlığı YOK.
    (d / "ornek_en.txt").write_text(DRAFT, encoding="utf-8")
    tr = d / "ornek_tr.txt"
    tr.write_text(DRAFT, encoding="utf-8")
    return d, tr


def _document_xml(out):
    with zipfile.ZipFile(out) as zf:
        return zf.read("word/document.xml").decode("utf-8")


def _has_footnotes_part(out):
    with zipfile.ZipFile(out) as zf:
        return "word/footnotes.xml" in zf.namelist()


# --- (1) DİPNOT KİPİ --------------------------------------------------------

def test_footnote_mode_auto_keeps(tmp_path):
    _, tr = _make_doc_dir(tmp_path)
    info = export_article_docx(tr, tr.with_suffix(".docx"), style={"footnotes": "auto"})
    assert info["footnote_mode"] == "auto"
    assert info["real_footnotes"] == 3
    assert _has_footnotes_part(info["output"])
    xml = _document_xml(info["output"])
    assert "footnoteReference" in xml
    assert "Dipnotlar" in xml  # fn 2 referanssız -> Dipnotlar bölümü


def test_footnote_mode_on_keeps(tmp_path):
    _, tr = _make_doc_dir(tmp_path)
    info = export_article_docx(tr, tr.with_suffix(".docx"), style={"footnotes": "on"})
    assert info["footnote_mode"] == "on"
    assert info["warnings"] == []
    assert _has_footnotes_part(info["output"])
    xml = _document_xml(info["output"])
    assert "footnoteReference" in xml
    assert "Dipnotlar" in xml


def test_footnote_mode_off_strips_everything(tmp_path):
    _, tr = _make_doc_dir(tmp_path)
    info = export_article_docx(tr, tr.with_suffix(".docx"), style={"footnotes": "off"})
    assert info["footnote_mode"] == "off"
    assert info["real_footnotes"] == 0
    assert not _has_footnotes_part(info["output"])  # dipnotlar bölümü YOK
    xml = _document_xml(info["output"])
    assert "[fn " not in xml                    # hiç gönderme kalmadı
    assert "footnoteReference" not in xml
    assert "Dipnotlar" not in xml               # Dipnotlar bölümü YOK
    assert "anlatır." in xml                    # cümle temiz bitti
    assert "[fn 1]" not in xml


def test_footnote_mode_on_without_footnotes_warns(tmp_path):
    d = tmp_path / "yok"
    d.mkdir()
    (d / "x_en.txt").write_text(DRAFT_NO_FN, encoding="utf-8")
    tr = d / "x_tr.txt"
    tr.write_text(DRAFT_NO_FN, encoding="utf-8")
    info = export_article_docx(tr, tr.with_suffix(".docx"), style={"footnotes": "on"})
    assert info["footnote_mode"] == "on"
    assert any("dipnot yok" in w for w in info["warnings"])


def test_resolve_footnote_mode_bool_alias():
    assert resolve_footnote_mode({"footnotes": True}) == "on"
    assert resolve_footnote_mode({"footnotes": False}) == "off"
    assert resolve_footnote_mode({}) == "auto"
    assert resolve_footnote_mode({"footnotes": "OFF"}) == "off"
    assert resolve_footnote_mode({"footnotes": "garip"}) == "auto"


# --- (2) İÇİNDEKİLER --------------------------------------------------------

def test_toc_auto_no_source_toc_excluded(tmp_path):
    _, tr = _make_doc_dir(tmp_path)
    info = export_article_docx(tr, tr.with_suffix(".docx"), style={"toc": "auto"})
    assert info["toc_mode"] == "auto" and info["toc_included"] is False
    assert "İçindekiler" not in _document_xml(info["output"])


def test_toc_true_forces(tmp_path):
    _, tr = _make_doc_dir(tmp_path)
    info = export_article_docx(tr, tr.with_suffix(".docx"), style={"toc": True})
    assert info["toc_included"] is True and info["toc_mode"] == "on"
    assert "İçindekiler" in _document_xml(info["output"])


def test_toc_false_forces_off(tmp_path):
    # Taslakta [TOC] olsa bile false zorlar.
    d = tmp_path / "tocval"
    d.mkdir()
    text = "[TITLE]\nT\n[/TITLE]\n[TOC]\n- Giriş\n[/TOC]\n[BODY]\np1: x.\n[/BODY]\n"
    (d / "y_en.txt").write_text(text, encoding="utf-8")
    tr = d / "y_tr.txt"
    tr.write_text(text, encoding="utf-8")
    info = export_article_docx(tr, tr.with_suffix(".docx"), style={"toc": False})
    assert info["toc_included"] is False
    assert "İçindekiler" not in _document_xml(info["output"])


def test_toc_auto_source_heading_included(tmp_path):
    d = tmp_path / "srctoc"
    d.mkdir()
    src = "[TITLE]\nBaşlık\n[/TITLE]\nContents\n[BODY]\np1: x.\n[/BODY]\n"
    (d / "z_en.txt").write_text(src, encoding="utf-8")
    tr = d / "z_tr.txt"
    tr.write_text(DRAFT.replace("[AUTHOR]\nEray Alim\n[/AUTHOR]\n", ""), encoding="utf-8")
    info = export_article_docx(tr, tr.with_suffix(".docx"), style={"toc": "auto"})
    assert info["toc_included"] is True
    assert "İçindekiler" in _document_xml(info["output"])


def test_toc_auto_draft_toc_block_included(tmp_path):
    d = tmp_path / "drafttoc"
    d.mkdir()
    text = "[TITLE]\nT\n[/TITLE]\n[TOC]\n- Giriş\n- Sonuç\n[/TOC]\n[BODY]\np1: x.\n[/BODY]\n"
    (d / "w_en.txt").write_text(text, encoding="utf-8")
    tr = d / "w_tr.txt"
    tr.write_text(text, encoding="utf-8")
    info = export_article_docx(tr, tr.with_suffix(".docx"), style={"toc": "auto"})
    assert info["toc_included"] is True
    assert "İçindekiler" in _document_xml(info["output"])


def test_source_contains_toc_heading_variants():
    assert source_contains_toc_heading("İçindekiler")
    assert source_contains_toc_heading("Table of Contents")
    assert source_contains_toc_heading("contents")
    assert source_contains_toc_heading("الفهرس")
    assert source_contains_toc_heading("[TOC]\n- Giriş\n[/TOC]")
    assert not source_contains_toc_heading("[TITLE]\nBaşlık\n[/TITLE]\n[BODY]\np1: x.\n[/BODY]")


# --- (3) YAZAR / KURUM ------------------------------------------------------

def test_author_institution_rendered(tmp_path):
    _, tr = _make_doc_dir(tmp_path)
    info = export_article_docx(tr, tr.with_suffix(".docx"), style={})
    assert info["author"] == "Eray Alim"
    assert info["institution"] == "Ankara Üniversitesi, Siyaset Bilimi"
    xml = _document_xml(info["output"])
    assert "Eray Alim" in xml
    assert "Ankara Üniversitesi, Siyaset Bilimi" in xml

    from docx import Document as open_docx

    doc = open_docx(info["output"])
    inst_paras = [p for p in doc.paragraphs if "Ankara Üniversitesi" in p.text]
    assert inst_paras, "kurum paragrafı bulunamadı"
    assert all(r.italic for r in inst_paras[0].runs if r.text.strip())


def test_affiliation_alias(tmp_path):
    text = "[TITLE]\nT\n[/TITLE]\n[AFFILIATION]\nBir Üniversite\n[/AFFILIATION]\n[BODY]\np1: x.\n[/BODY]\n"
    doc = parse_document(text)
    assert doc.institution == "Bir Üniversite"
    assert "[INSTITUTION]" in serialize_document(doc)


def test_config_fallback_author_institution(tmp_path):
    d = tmp_path / "fallback"
    d.mkdir()
    (d / "f_en.txt").write_text(DRAFT_NO_FN, encoding="utf-8")
    tr = d / "f_tr.txt"
    tr.write_text(DRAFT_NO_FN, encoding="utf-8")
    style = {"author": "Config Yazar", "institution": "Config Kurum"}
    info = export_article_docx(tr, tr.with_suffix(".docx"), style=style)
    assert info["author"] == "Config Yazar"
    assert info["institution"] == "Config Kurum"
    xml = _document_xml(info["output"])
    assert "Config Yazar" in xml and "Config Kurum" in xml


def test_draft_author_overrides_config(tmp_path):
    _, tr = _make_doc_dir(tmp_path)
    info = export_article_docx(
        tr, tr.with_suffix(".docx"), style={"author": "Yanlış", "institution": "Yanlış"}
    )
    assert info["author"] == "Eray Alim"


# --- CONFIG + VALIDATOR + PROMPT -------------------------------------------

def test_default_docx_new_keys():
    assert DEFAULT_DOCX["toc"] == "auto"
    assert DEFAULT_DOCX["footnotes"] == "auto"
    assert DEFAULT_DOCX["author"] == ""
    assert DEFAULT_DOCX["institution"] == ""


def test_config_cascade_footnotes_mode(tmp_path):
    root = tmp_path / "documents"
    doc = root / "vaka"
    doc.mkdir(parents=True)
    (root / "config.json").write_text('{"docx": {"footnotes": "on"}}', encoding="utf-8")
    (doc / "config.json").write_text('{"docx": {"toc": true}}', encoding="utf-8")
    cfg = load_config(doc, docs_root=root)
    assert cfg["docx"]["footnotes"] == "on"    # kökten miras
    assert cfg["docx"]["toc"] is True          # yerde ezildi
    assert cfg["docx"]["author"] == ""         # varsayılan korunur
    assert validate_config_dict({"docx": {}}) == []


def test_byline_hint_true_and_false():
    seyahat = "[TITLE]Turkey's Post-Colonial Predicament (1955-1959)[/TITLE]\n" \
              '[SUBTITLE title="Eray Alim, Middle Eastern Studies 58/6 (2022), ss. 972-988"]\n[BODY]\np1: x.\n[/BODY]\n'
    assert byline_hint(seyahat) is True
    assert byline_hint("[TITLE]Sade Başlık[/TITLE]\n[BODY]\np1: x.\n[/BODY]\n") is False


def test_validate_warns_missing_author(tmp_path):
    d = tmp_path / "val"
    d.mkdir()
    src = "[TITLE]Sade Başlık[/TITLE]\n" \
          '[SUBTITLE title="Eray Alim, Middle Eastern Studies 58/6 (2022), ss. 972-988"]\n' \
          "[BODY]\np1: x.\n[/BODY]\n"
    (d / "v_en.txt").write_text(src, encoding="utf-8")
    tr = d / "v_tr.txt"
    tr.write_text("[TITLE]\nSade Başlık\n[/TITLE]\n[BODY]\np1: x.\n[/BODY]\n", encoding="utf-8")
    warnings = validate_pair(d / "v_en.txt", tr)
    assert any("yazar/kurum" in w.lower() for w in warnings)


def test_validate_no_warn_when_author_present(tmp_path):
    d = tmp_path / "val2"
    d.mkdir()
    src = "[TITLE]\nT\n[/TITLE]\n[AUTHOR]\nEray Alim\n[/AUTHOR]\n[BODY]\np1: x.\n[/BODY]\n"
    (d / "u_en.txt").write_text(src, encoding="utf-8")
    tr = d / "u_tr.txt"
    tr.write_text(src, encoding="utf-8")
    warnings = validate_pair(d / "u_en.txt", tr)
    assert not any("yazar/kurum" in w.lower() for w in warnings)


def test_prompt_carries_mode_and_byline(tmp_path, monkeypatch):
    import makale_pipeline.config as C
    import makale_pipeline.translator as T

    d = tmp_path / "prompt"
    d.mkdir()
    (d / "p_en.txt").write_text(DRAFT, encoding="utf-8")
    (d / "config.json").write_text('{"docx": {"footnotes": "off"}}', encoding="utf-8")
    monkeypatch.setattr(T, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(C, "DOCUMENTS_DIR", tmp_path)
    prompt = T.build_prompt(d / "p_en.txt")
    assert "Dipnot kipi: OFF" in prompt
    assert "[AUTHOR]" in prompt and "[INSTITUTION]" in prompt
