"""Yapılandırılmış TXT biçiminin ayrıştırıcısı ve serileştiricisi.

Biçim:
    [TITLE] ... [/TITLE]  (tek satırlık başlık da desteklenir)
    [SUBTITLE] ... [/SUBTITLE]
    [AUTHOR] ... [/AUTHOR]              (yazar; tek satır)
    [INSTITUTION] ... [/INSTITUTION]    ([AFFILIATION] eşanlamlı)
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

_QUOTE_CHARS = "“”\"'‘’"
SECTION_RE = re.compile(r"\[SECTION(?P<attrs>[^\]]*)\]")
SUBSECTION_RE = re.compile(r"\[SUBSECTION(?P<attrs>[^\]]*)\]")
MARKER_ATTR_RE = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[" + _QUOTE_CHARS + r"]([^" + _QUOTE_CHARS + r"]*)[" + _QUOTE_CHARS + r"]"
)


def marker_attr(text: str, name: str) -> str:
    """`[TAG ... name=“değer”]` işaretçisinden özniteliği okur (tırnak türü esnek)."""
    match = re.search(
        rf"\b{re.escape(name)}\s*=\s*[{_QUOTE_CHARS}]([^{_QUOTE_CHARS}]*)[{_QUOTE_CHARS}]",
        text or "",
    )
    return match.group(1).strip() if match else ""


def single_marker_value(lines: list[str], tag: str) -> str:
    """Kapanışsız tek işaretçiyi okur: `[TAG title="X"]` veya `[TAG X]`.

    Taslaklarda üstbilgi işaretçileri iki biçimde yazılabiliyor; kapanışsız
    biçim eskiden hiç okunmuyordu ve yazar/kurum satırı kayboluyordu
    (`[SUBTITLE title="Yazar, Dergi …"]`).
    """
    pattern = re.compile(rf"\[{tag}(?P<attrs>[^\]]*)\]")
    for line in lines:
        match = pattern.match(line.strip())
        if not match:
            continue
        attrs = match.group("attrs")
        value = marker_attr(attrs, "title") or marker_attr(attrs, "value")
        if value:
            return value
        value = attrs.strip()
        if value:
            return value
    return ""
PARA_RE = re.compile(r"^p(\d+)\s*:\s*(.*)$")
FOOTNOTE_RE = re.compile(r"^(\d+)\s*:\s*(.*)$")
FN_REF_RE = re.compile(r"\[fn\s+(\d+)\]")

# Kaynak metinde gerçek bir içindekiler başlığı sayılan satırlar.
TOC_HEADING_RE = re.compile(
    r"^\s*(?:i[cç]indekiler|contents|table\s+of\s+contents|i[̇]?ndeks|fihrist"
    r"|الفهرس|فهرس)\s*:?\s*$",
    re.IGNORECASE,
)

# Yazar/kurum satırı sinyali (uydurmadan yalnızca raporlama için).
BYLINE_HINT_RE = re.compile(
    r"(?:"
    r"\b(?:Dr|Prof|Doç|Assoc|Asst|Öğr|Yrd|Yar)\.?"          # akademik unvan
    r"|\b(?:University|Üniversitesi|Department|Bölümü|Faculty|Fakültesi"
    r"|Institute|Enstitüsü|College|School|Press|Journal|Studies|Dergisi)\b"
    r"|\bss\.\s*\d"                                          # "ss. 972"
    r"|\(\s*(?:19|20)\d{2}\s*\)"                             # "(2022)"
    r")",
    re.IGNORECASE,
)

_PREAMBLE_TAG_RE = re.compile(r"^\[(/?)([A-Z_]+)(?:\s+[^\]]*)?\]$")
_TAG_ATTR_RE = re.compile(r'\[/?[A-Z_]+(?:\s+([A-Za-z_]+)="([^"]*)")?[^\]]*\]')


def _block_value(lines: list[str], tag: str) -> str:
    """[TAG]...[/TAG] bloğunu veya tek satırlık [TAG] değer satırını okur."""
    return _block_value_any(lines, (tag,))


def _block_value_any(lines: list[str], tags: tuple[str, ...]) -> str:
    """Verilen etiketlerden ilk dolu bloğun değerini döndürür (eşanlamlı desteği).

    İki biçim desteklenir:
      çok satırlı:  [TAG]\\n değer \\n[/TAG]
      tek satırlı:  [TAG]değer[/TAG]     (çeviri taslaklarında sık görülür)
    Tek satırlı biçim eskiden okunmuyordu; başlık/alt başlık/yazar kayboluyordu.
    """
    text = "\n".join(lines)
    for tag in tags:
        match = re.search(rf"\[{tag}\](.*?)\[/{tag}\]", text, re.S | re.I)
        if match:
            value = "\n".join(p.strip() for p in match.group(1).splitlines()).strip()
            if value:
                return value
    # Kapanışsız tek işaretçi biçimi: [TAG title="…"] / [TAG …]
    for tag in tags:
        value = single_marker_value(lines, tag)
        if value:
            return value
    return ""


def source_contains_toc_heading(text: str) -> bool:
    """Kaynak metin gerçekten bir içindekiler başlığı taşıyor mu?

    [TOC] bloğundaki girişler de sayılır. Uydurma TOC üretmemek için
    yalnızca bu işaret varken içindekiler eklenmesi gerekir.
    """
    in_toc = False
    for line in text.splitlines():
        s = line.strip()
        if s == "[TOC]":
            in_toc = True
            continue
        if s == "[/TOC]":
            in_toc = False
            continue
        if in_toc and s.startswith("-") and s[1:].strip():
            return True
        if TOC_HEADING_RE.match(s):
            return True
    return False


def byline_hint(source_text: str) -> bool:
    """Kaynağın ilk satırları yazar/kurum taşıyor gibi mi görünüyor?

    Yalnızca doğrulama uyarısı içindir; hiçbir değer uydurulmaz.
    [TITLE] bloğu dışlanır (başlıktaki yıl parantezi yanlış sinyal vermesin).
    """
    head = source_text.split("[BODY]", 1)[0]
    # Başlık bloklarını (tek satırlık [TITLE]...[/TITLE] dahil) çıkar.
    head = re.sub(r"\[TITLE\].*?\[/TITLE\]", "", head, flags=re.DOTALL)
    chunks: list[str] = []
    for line in head.splitlines():
        s = line.strip()
        if not s:
            continue
        m = _PREAMBLE_TAG_RE.match(s)
        if m:
            # Nitelikli tek satırlık etiket (ör. [SUBTITLE title="Eray Alim, ..."])
            for _attr, value in _TAG_ATTR_RE.findall(s):
                if value.strip():
                    chunks.append(value.strip())
            continue
        chunks.append(s)
    blob = "\n".join(chunks)
    return bool(BYLINE_HINT_RE.search(blob))


def is_structured_document(text: str) -> bool:
    return "[BODY]" in text and "[/BODY]" in text


def extract_fn_refs(text: str) -> set[str]:
    return set(FN_REF_RE.findall(text))


def parse_document(text: str) -> StructuredDocument:
    doc = StructuredDocument()
    lines = text.splitlines()

    doc.title = _block_value(lines, "TITLE")
    doc.subtitle = _block_value(lines, "SUBTITLE")
    doc.author = _block_value(lines, "AUTHOR")
    doc.institution = _block_value_any(lines, ("INSTITUTION", "AFFILIATION"))
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
            attrs = m_sec.group("attrs")
            current = Section(
                section_id=marker_attr(attrs, "id") or f"sec{len(doc.sections) + 1}",
                title=marker_attr(attrs, "title") or "GÖVDE",
            )
            doc.sections.append(current)
            continue
        if s == "[/SECTION]":
            current = None
            continue
        m_sub = SUBSECTION_RE.match(s)
        if m_sub:
            title = marker_attr(m_sub.group("attrs"), "title") or "Alt başlık"
            ensure_section().subsections.append(Subsection(title=title))
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
    if doc.author:
        lines += ["[AUTHOR]", doc.author, "[/AUTHOR]", ""]
    if doc.institution:
        lines += ["[INSTITUTION]", doc.institution, "[/INSTITUTION]", ""]
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
