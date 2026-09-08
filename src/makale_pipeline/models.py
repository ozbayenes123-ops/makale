"""Yapılandırılmış TXT belgesinin veri modelleri."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TocEntry:
    label: str
    anchor: str


@dataclass
class Paragraph:
    num: str
    text: str


@dataclass
class Subsection:
    title: str


@dataclass
class Section:
    section_id: str
    title: str
    paragraphs: list[Paragraph] = field(default_factory=list)
    subsections: list[Subsection] = field(default_factory=list)


@dataclass
class Footnote:
    num: str
    text: str


@dataclass
class StructuredDocument:
    title: str = ""
    subtitle: str = ""
    vat_label: str = ""
    toc: list[TocEntry] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    footnotes: list[Footnote] = field(default_factory=list)
    is_structured: bool = False

    @property
    def paragraph_count(self) -> int:
        return sum(len(s.paragraphs) for s in self.sections)

    @property
    def footnote_count(self) -> int:
        return len(self.footnotes)

    def body_text(self) -> str:
        """Tüm paragraf metinlerini birleştirir (uzunluk/istatistik için)."""
        return "\n".join(
            p.text for s in self.sections for p in s.paragraphs
        )

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "vat_label": self.vat_label,
            "toc": [{"label": t.label, "anchor": t.anchor} for t in self.toc],
            "sections": [
                {
                    "id": s.section_id,
                    "title": s.title,
                    "subsections": [sub.title for sub in s.subsections],
                    "paragraphs": [
                        {"num": p.num, "text": p.text} for p in s.paragraphs
                    ],
                }
                for s in self.sections
            ],
            "footnotes": [{"num": f.num, "text": f.text} for f in self.footnotes],
            "paragraph_count": self.paragraph_count,
            "footnote_count": self.footnote_count,
        }
