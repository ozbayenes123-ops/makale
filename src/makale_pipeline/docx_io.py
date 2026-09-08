# -*- coding: utf-8 -*-
"""DOCX okuma/yazma: Word belgesi <-> yapılandırılmış taslak.

read_docx: Bir .docx dosyasını paragraf stillerine bakarak [TITLE]/[SECTION]/
p<n>: taslağına döker; varsa dipnotları word/footnotes.xml'den çeker.

export_docx: Yapılandırılmış _tr.txt dosyasını biçimli bir Word belgesine
(Başlık, H1 bölümler, gövde, Dipnotlar bölümü) derler.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from docx import Document as open_docx

from makale_pipeline.models import Footnote

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _read_footnotes(docx_path: Path) -> list[Footnote]:
    """word/footnotes.xml'den dipnotları çeker (ayraç dipnotları hariç)."""
    try:
        with zipfile.ZipFile(docx_path) as zf:
            if "word/footnotes.xml" not in zf.namelist():
                return []
            root = ElementTree.fromstring(zf.read("word/footnotes.xml"))
    except (OSError, ElementTree.ParseError):
        return []
    notes: list[Footnote] = []
    for fn in root.findall(f"{_W_NS}footnote"):
        fid = fn.get(f"{_W_NS}id")
        if fid is None or int(fid) < 1:
            continue  # -1/0 ayraç dipnotları
        text = "".join(t.text or "" for t in fn.iter(f"{_W_NS}t")).strip()
        if text:
            notes.append(Footnote(fid, text))
    return notes


def _para_footnote_ids(docx_path: Path) -> list[list[str]]:
    """document.xml'deki paragrafların dipnot gönderimlerini sırayla çıkarır.

    Dönen liste, _docx_to_structured'daki gövde paragraflarıyla aynı sıradadır;
    her öğe o paragraftaki footnote id listesidir.
    """
    try:
        with zipfile.ZipFile(docx_path) as zf:
            if "word/document.xml" not in zf.namelist():
                return []
            root = ElementTree.fromstring(zf.read("word/document.xml"))
    except (OSError, ElementTree.ParseError):
        return []
    out: list[list[str]] = []
    for para in root.iter(f"{_W_NS}p"):
        ids = [
            fr.get(f"{_W_NS}id")
            for fr in para.iter(f"{_W_NS}footnoteReference")
            if fr.get(f"{_W_NS}id") is not None
        ]
        # Sadece gövde paragrafı sayılanlara (metin içeren) karşılık için
        # tüm paragrafları kaydet; eşleme metin bazında hizalanır.
        text = "".join(t.text or "" for t in para.iter(f"{_W_NS}t")).strip()
        out.append((text, ids))
    return out


def _norm_text(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def _docx_to_structured(docx_path: Path) -> str:
    """DOCX paragraf stillerini yapılandırılmış TXT etiketlerine çevirir.

    Metin-içi dipnot gönderimleri korunur: document.xml'deki
    footnoteReference sırasına göre paragraflara [fn N] işaretleri eklenir.
    """
    doc = open_docx(str(docx_path))
    xml_paras = _para_footnote_ids(docx_path)
    xml_idx = 0
    id2num: dict[str, str] = {}

    def take_ids(norm: str) -> list[str]:
        nonlocal xml_idx
        while xml_idx < len(xml_paras):
            t, ids = xml_paras[xml_idx]
            xml_idx += 1
            if _norm_text(t) == norm:
                return ids
        return []

    def num_of(fid: str) -> str:
        if fid not in id2num:
            id2num[fid] = str(len(id2num) + 1)
        return id2num[fid]

    title = ""
    subtitle = ""
    body_items: list[str] = []
    p_counter = 1
    sec_counter = 0
    section_open = False

    for para in doc.paragraphs:
        style = (para.style.name or "").lower() if para.style is not None else ""
        text = para.text.strip()
        if not text:
            continue
        if "title" in style and "subtitle" not in style:
            title = title or text
            take_ids(_norm_text(text))
            continue
        if "subtitle" in style:
            subtitle = subtitle or text
            take_ids(_norm_text(text))
            continue
        if style.startswith("heading 1") or style.startswith("başlık 1"):
            if section_open:
                body_items.append("[/SECTION]")
            sec_counter += 1
            take_ids(_norm_text(text))
            body_items.append(f'[SECTION id="sec{sec_counter}" title="{text}"]')
            section_open = True
            continue
        if style.startswith("heading") or style.startswith("başlık"):
            take_ids(_norm_text(text))
            body_items.append(f'[SUBSECTION title="{text}"]')
            continue
        clean = re.sub(r"\s+", " ", text)
        markers = "".join(f" [fn {num_of(fid)}]" for fid in take_ids(clean))
        body_items.append(f"p{p_counter}: {clean}{markers}")
        p_counter += 1

    if section_open:
        body_items.append("[/SECTION]")

    lines: list[str] = []
    if title:
        lines.extend(["[TITLE]", title, "[/TITLE]", ""])
    if subtitle:
        lines.extend(["[SUBTITLE]", subtitle, "[/SUBTITLE]", ""])
    lines.append("[BODY]")
    lines.extend(body_items)
    lines.append("[/BODY]")

    footnotes = _read_footnotes(docx_path)
    if footnotes or id2num:
        by_id = {fn.num: fn.text for fn in footnotes}
        ordered = sorted(id2num.items(), key=lambda kv: int(kv[1]))
        lines.append("")
        lines.append("[FOOTNOTES]")
        for fid, num in ordered:
            if fid in by_id:
                lines.append(f"{num}: {by_id[fid]}")
        for fn in footnotes:
            if fn.num not in id2num:
                lines.append(f"{fn.num}: {fn.text}")
        lines.append("[/FOOTNOTES]")
    return "\n".join(lines)


def read_docx(docx_path: Path | str, output_path: Path | str | None = None) -> dict:
    """DOCX'i yapılandırılmış taslağa döker; output verilirse dosyaya yazar."""
    src = Path(docx_path)
    if not src.exists():
        raise FileNotFoundError(f"DOCX bulunamadı: {src}")
    draft = _docx_to_structured(src)
    out = Path(output_path) if output_path else src.with_suffix(".draft.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(draft, encoding="utf-8")
    return {
        "source": str(src),
        "output": str(out),
        "paragraphs": sum(1 for line in draft.splitlines() if re.match(r"^p\d+:", line.strip())),
        "footnotes": sum(1 for line in draft.splitlines() if re.match(r"^\d+:", line.strip())),
        "has_title": bool(draft.startswith("[TITLE]")),
    }


def export_docx(
    translation_path: Path | str,
    output_path: Path | str | None = None,
    style: dict | None = None,
) -> dict:
    """Yapılandırılmış _tr.txt dosyasını makale formatında Word'e derler.

    Basit derleyici tarihe karıştı; makale derleyiciye delege eder.
    """
    from makale_pipeline.article_docx import export_article_docx
    from makale_pipeline.config import load_config

    tr = Path(translation_path)
    cfg = style if style is not None else load_config(tr.parent).get("docx", {})
    return export_article_docx(tr, output_path, style=cfg)
