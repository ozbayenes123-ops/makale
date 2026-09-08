"""Yapılandırılmış TXT biçiminin ayrıştırıcısı ve serileştiricisi.

Biçim:
    [TITLE] ... [/TITLE]  (tek satırlık başlık da desteklenir)
    [SUBTITLE] ... [/SUBTITLE]
    [VAT_LABEL] ... [/VAT_LABEL]
    [BODY]
    [SECTION id="sec1" title="Giriş"]
    [SUBSECTION title="Alt başlık"]
    p1: paragraf metni...
    [/SECTION]
    [/BODY]
    [FOOTNOTES]
    1: dipnot metni...
    [/FOOTNOTES]

Dipnot göndermeleri metin içinde [fn 1] biçimindedir.
"""

from __future__ import annotations

import re
from pathlib import Path

from makale_pipeline.models import (
    Footnote,
    Paragraph,
    Section,
    StructuredDocument,
    Subsection,
    TocEntry,
)

SECTION_RE = re.compile(r'\[SECTION\s+id="([^"]*)"\s+title="([^"]*)"\s*\]')
SUBSECTION_RE = re.compile(r'\[SUBSECTION\s+title="([^"]*)"\s*\]')
PARA_RE = re.compile(r"^p(\d+)\s*:\s*(.*)$")
FOOTNOTE_RE = re.compile(r"^(\d+)\s*:\s*(.*)$")
FN_REF_RE = re.compile(r"\[fn\s+(\d+)\]")


def _block_value(lines: list[str], tag: str) -> str:
    """[TAG]...[/TAG] bloğunu veya tek satırlık [TAG] değer satırını okur."""
    open_tag = f"[{tag}]"
    close_tag = f"[/{tag}]"
    collecting = False
    buf: list[str] = []
    for line in lines:
        s = line.strip()
        if not collecting:
            if s == open_tag:
                collecting = True
                continue
            continue
        if s == close_tag:
            break
        buf.append(line.rstrip("\n"))
    return "\n".join(buf).strip()


def is_structured_document(text: str) -> bool:
    return "[BODY]" in text and "[/BODY]" in text


def extract_fn_refs(text: str) -> set[str]:
    return set(FN_REF_RE.findall(text))


def parse_document(text: str) -> StructuredDocument:
    doc = StructuredDocument()
    lines = text.splitlines()

    doc.title = _block_value(lines, "TITLE")
    doc.subtitle = _block_value(lines, "SUBTITLE")
    doc.vat_label = _block_value(lines, "VAT_LABEL")

    # TOC satırları: "- etiket" (bağlantı bilgisi korunmaz, yeniden üretilir)
    in_toc = False
    for line in lines:
        s = line.strip()
        if s == "[TOC]":
            in_toc = True
            continue
        if s == "[/TOC]":
            break
        if in_toc and s.startswith("-"):
            label = s[1:].strip()
            if label:
                doc.toc.append(TocEntry(label=label, anchor=""))

    in_body = False
    in_footnotes = False
    current: Section | None = None

    def ensure_section() -> Section:
        nonlocal current
        if current is None:
            current = Section(section_id="govde", title="GÖVDE")
            doc.sections.append(current)
        return current

    for line in lines:
        s = line.strip()
        if s == "[BODY]":
            in_body = True
            continue
        if s == "[/BODY]":
            in_body = False
            continue
        if s == "[FOOTNOTES]":
            in_footnotes = True
            continue
        if s == "[/FOOTNOTES]":
            in_footnotes = False
            continue
        if in_footnotes:
            m = FOOTNOTE_RE.match(s)
            if m:
                doc.footnotes.append(Footnote(num=m.group(1), text=m.group(2).strip()))
            continue
        if not in_body:
            continue
        m_sec = SECTION_RE.match(s)
        if m_sec:
            current = Section(section_id=m_sec.group(1), title=m_sec.group(2))
            doc.sections.append(current)
            continue
        if s == "[/SECTION]":
            current = None
            continue
        m_sub = SUBSECTION_RE.match(s)
        if m_sub:
            ensure_section().subsections.append(Subsection(title=m_sub.group(1)))
            continue
        m_para = PARA_RE.match(s)
        if m_para:
            ensure_section().paragraphs.append(
                Paragraph(num=m_para.group(1), text=m_para.group(2).strip())
            )
            continue
        if s:
            # Numarasız devam satırı: son paragrafa ekle.
            sec = ensure_section()
            if sec.paragraphs:
                sec.paragraphs[-1].text += " " + s
            else:
                sec.paragraphs.append(Paragraph(num="", text=s))

    doc.is_structured = is_structured_document(text)
    return doc


def parse_file(path: str | Path) -> StructuredDocument:
    return parse_document(Path(path).read_text(encoding="utf-8"))


def serialize_document(doc: StructuredDocument) -> str:
    lines: list[str] = []
    if doc.title:
        lines += ["[TITLE]", doc.title, "[/TITLE]", ""]
    if doc.subtitle:
        lines += ["[SUBTITLE]", doc.subtitle, "[/SUBTITLE]", ""]
    if doc.vat_label:
        lines += ["[VAT_LABEL]", doc.vat_label, "[/VAT_LABEL]", ""]
    lines.append("[BODY]")
    for sec in doc.sections:
        if not (sec.section_id == "govde" and sec.title == "GÖVDE"):
            lines.append(f'[SECTION id="{sec.section_id}" title="{sec.title}"]')
        for sub in sec.subsections:
            lines.append(f'[SUBSECTION title="{sub.title}"]')
        for p in sec.paragraphs:
            prefix = f"p{p.num}: " if p.num else ""
            lines.append(f"{prefix}{p.text}")
        if not (sec.section_id == "govde" and sec.title == "GÖVDE"):
            lines.append("[/SECTION]")
    lines.append("[/BODY]")
    if doc.footnotes:
        lines += ["", "[FOOTNOTES]"]
        for fn in doc.footnotes:
            lines.append(f"{fn.num}: {fn.text}")
        lines.append("[/FOOTNOTES]")
    return "\n".join(lines) + "\n"
