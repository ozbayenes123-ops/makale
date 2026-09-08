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
from docx.shared import Pt

from makale_pipeline.models import Footnote
from makale_pipeline.structured import parse_file

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


def _docx_to_structured(docx_path: Path) -> str:
    """DOCX paragraf stillerini yapılandırılmış TXT etiketlerine çevirir."""
    doc = open_docx(str(docx_path))
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
            continue
        if "subtitle" in style:
            subtitle = subtitle or text
            continue
        if style.startswith("heading 1") or style.startswith("başlık 1"):
            if section_open:
                body_items.append("[/SECTION]")
            sec_counter += 1
            body_items.append(f'[SECTION id="sec{sec_counter}" title="{text}"]')
            section_open = True
            continue
        if style.startswith("heading") or style.startswith("başlık"):
            body_items.append(f'[SUBSECTION title="{text}"]')
            continue
        clean = re.sub(r"\s+", " ", text)
        body_items.append(f"p{p_counter}: {clean}")
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
    if footnotes:
        lines.append("")
        lines.append("[FOOTNOTES]")
        for fn in footnotes:
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
) -> dict:
    """Yapılandırılmış _tr.txt dosyasını biçimli Word belgesine derler."""
    tr = Path(translation_path)
    if not tr.exists():
        raise FileNotFoundError(f"Çeviri dosyası yok: {tr}")
    doc_model = parse_file(tr)
    if not doc_model.is_structured:
        raise ValueError(f"Yapılandırılmamış belge değil ([BODY] yok): {tr.name}")

    doc = open_docx()
    if doc_model.title:
        doc.add_heading(doc_model.title, level=0)
    if doc_model.subtitle:
        p = doc.add_paragraph()
        r = p.add_run(doc_model.subtitle)
        r.italic = True

    for section in doc_model.sections:
        if section.title and section.title != "GÖVDE":
            doc.add_heading(section.title, level=1)
        for sub in section.subsections:
            doc.add_heading(sub.title, level=2)
        for para in section.paragraphs:
            if para.text:
                doc.add_paragraph(para.text)

    if doc_model.footnotes:
        doc.add_heading("Dipnotlar", level=1)
        for fn in doc_model.footnotes:
            p = doc.add_paragraph()
            r = p.add_run(f"{fn.num}. ")
            r.bold = True
            p.add_run(fn.text)
            p.paragraph_format.left_indent = Pt(12)

    out = Path(output_path) if output_path else tr.with_suffix(".docx")
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    return {
        "source": str(tr),
        "output": str(out),
        "paragraphs": doc_model.paragraph_count,
        "footnotes": doc_model.footnote_count,
    }
