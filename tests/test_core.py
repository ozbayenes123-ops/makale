# -*- coding: utf-8 -*-
"""Çekirdek testler: yapı, yol, config, QA, Word derleme, çeviri hattı."""

from pathlib import Path

import pytest

from makale_pipeline import PROJECT_ROOT
from makale_pipeline.article_docx import export_article_docx
from makale_pipeline.config import DEFAULT_CONFIG, load_config, validate_config_dict
from makale_pipeline.paths import (
    find_source_files,
    infer_lang,
    target_path_for_source,
)
from makale_pipeline.quality import scan_text
from makale_pipeline.structured import (
    extract_fn_refs,
    is_structured_document,
    parse_document,
    serialize_document,
)
from makale_pipeline.translation_qa import (
    check_glossary_coverage,
    check_numeric_coverage,
)
from makale_pipeline.translator import apply_translation, build_prompt

SAMPLE = """[TITLE]
Örnek Başlık
[/TITLE]

[BODY]
[SECTION id="sec1" title="Giriş"]
p1: İlk paragraf burada başlar ve 1971 yılında geçen bir olayı anlatır [fn 1].
p2: İkinci paragraf UNESCO kısaltmasını ve %12,5 oranını içerir.
[/SECTION]
[/BODY]

[FOOTNOTES]
1: Dipnot metni burada.
[/FOOTNOTES]
"""


@pytest.fixture()
def pair(tmp_path):
    src = tmp_path / "ornek_en.txt"
    src.write_text(SAMPLE.replace("UNESCO", "UNESCO").replace("1971", "1971"), encoding="utf-8")
    tr_text = SAMPLE
    tr = tmp_path / "ornek_tr.txt"
    tr.write_text(tr_text, encoding="utf-8")
    return src, tr


def test_structured_roundtrip():
    doc = parse_document(SAMPLE)
    assert doc.is_structured
    assert doc.title == "Örnek Başlık"
    assert doc.paragraph_count == 2
    assert doc.footnote_count == 1
    assert extract_fn_refs(SAMPLE) == {"1"}
    out = serialize_document(doc)
    doc2 = parse_document(out)
    assert doc2.paragraph_count == 2
    assert doc2.title == "Örnek Başlık"


def test_paths():
    assert infer_lang("belge_en.txt") == "en"
    assert infer_lang("metin_ar.txt") == "ar"
    assert target_path_for_source(Path("x/belge_en.txt")).name == "belge_tr.txt"
    assert target_path_for_source(Path("x/belge.txt")).name == "belge_tr.txt"


def test_config_defaults_and_schema():
    assert DEFAULT_CONFIG["output_formats"] == ["docx"]
    assert DEFAULT_CONFIG["docx"]["body_size_pt"] == 12
    assert validate_config_dict({"style": "academic", "docx": {}}) == []
    assert any("Bilinmeyen" in w for w in validate_config_dict({"xyz": 1}))


def test_numeric_coverage_ok(pair):
    src_doc = parse_document(pair[0].read_text(encoding="utf-8"))
    tr_doc = parse_document(pair[1].read_text(encoding="utf-8"))
    assert check_numeric_coverage(src_doc, tr_doc) == []


def test_numeric_coverage_missing(tmp_path):
    src = parse_document("[BODY]\np1: 1971 ve 1939-1945 geçti.\n[/BODY]")
    tr = parse_document("[BODY]\np1: Yıllar geçti.\n[/BODY]")
    warnings = check_numeric_coverage(src, tr)
    assert warnings and "1971" in warnings[0]


def test_glossary_coverage(tmp_path):
    src = parse_document("[BODY]\np1: The state controls the market.\n[/BODY]")
    tr_ok = parse_document("[BODY]\np1: Devlet piyasayı denetler.\n[/BODY]")
    tr_bad = parse_document("[BODY]\np1: Hükümet piyasayı denetler.\n[/BODY]")
    gloss = {"state": "devlet"}
    assert check_glossary_coverage(src, tr_ok, gloss) == []
    assert check_glossary_coverage(src, tr_bad, gloss) != []


def test_quality_banned():
    issues = scan_text("Bu oldukça önemli bir meseledir.")
    assert any(i["type"] == "yasakli_ifade" for i in issues)


def test_export_article_docx(pair):
    _, tr = pair
    info = export_article_docx(tr, tr.with_suffix(".docx"), style={})
    out = Path(info["output"])
    assert out.exists() and out.stat().st_size > 5000
    assert info["real_footnotes"] == 1
    import zipfile

    with zipfile.ZipFile(out) as zf:
        assert "word/footnotes.xml" in zf.namelist()
        fx = zf.read("word/footnotes.xml").decode("utf-8")
        assert "Dipnot metni" in fx


def test_build_prompt_has_qa(tmp_path, monkeypatch):
    src = tmp_path / "a_en.txt"
    src.write_text(SAMPLE, encoding="utf-8")
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    import makale_pipeline.translator as T

    monkeypatch.setattr(T, "PROJECT_ROOT", tmp_path.parent)
    prompt = build_prompt(src)
    assert "ÖZ DENETİM" in prompt
    assert "1971" in prompt


def test_apply_translation_docx_first(pair, monkeypatch):
    import makale_pipeline.translator as T

    monkeypatch.setattr(T, "PROJECT_ROOT", pair[1].parent)
    res = apply_translation(pair[0], pair[1])
    assert res["ok"] is True
    assert res["docx"] is not None
