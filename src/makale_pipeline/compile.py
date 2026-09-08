"""TXT -> HTML derleme (ikincil çıktı; birincil çıktı Word'dür).

Şablon yer tutucuları: {{title}}, {{subtitle}}, {{toc}}, {{content}},
{{footnotes}}. [fn N] göndermeleri üstsimge dipnot bağlantılarına dönüşür.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from makale_pipeline.structured import FN_REF_RE, parse_file

__all__ = ["compile_document", "check_html_file", "render_html"]


def _link_fn_refs(text: str) -> str:
    def _rep(m: re.Match) -> str:
        n = m.group(1)
        return f'<sup class="fnref"><a href="#fn{n}">[{n}]</a></sup>'

    return FN_REF_RE.sub(_rep, html.escape(text))


def render_html(tr_path: Path, template_text: str) -> str:
    doc = parse_file(tr_path)
    if not doc.is_structured:
        raise ValueError(f"Yapılandırılmamış belge ([BODY] yok): {tr_path.name}")

    toc_items = []
    body_parts = []
    for sec in doc.sections:
        anchor = sec.section_id or "govde"
        if sec.title and sec.title != "GÖVDE":
            toc_items.append(f'<li><a href="#{anchor}">{html.escape(sec.title)}</a></li>')
            body_parts.append(f'<h2 id="{anchor}">{html.escape(sec.title)}</h2>')
        for sub in sec.subsections:
            body_parts.append(f"<h3>{html.escape(sub.title)}</h3>")
        for para in sec.paragraphs:
            if para.text:
                body_parts.append(f"<p>{_link_fn_refs(para.text)}</p>")

    toc = f"<ul>{''.join(toc_items)}</ul>" if toc_items else ""
    footnotes = ""
    if doc.footnotes:
        items = "".join(
            f'<li id="fn{fn.num}">{_link_fn_refs(fn.text)}</li>'
            for fn in doc.footnotes
        )
        footnotes = f"<h2>Dipnotlar</h2><ol>{items}</ol>"

    out = template_text
    out = out.replace("{{title}}", html.escape(doc.title or tr_path.stem))
    out = out.replace("{{subtitle}}", html.escape(doc.subtitle or ""))
    out = out.replace("{{toc}}", toc)
    out = out.replace("{{content}}", "\n".join(body_parts))
    out = out.replace("{{footnotes}}", footnotes)
    return out


def compile_document(tr_path: Path, template_path: Path, out_path: Path) -> bool:
    """Tek çeviriyi HTML'e derler; başarıda True."""
    try:
        template_text = Path(template_path).read_text(encoding="utf-8")
        rendered = render_html(Path(tr_path), template_text)
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        return True
    except (OSError, ValueError):
        return False


def check_html_file(html_path: Path, verbose: bool = False) -> list[str]:
    """Derlenen HTML'de temel sorunları listeler (boşsa temiz)."""
    issues: list[str] = []
    p = Path(html_path)
    if not p.exists():
        return [f"HTML yok: {p}"]
    text = p.read_text(encoding="utf-8")
    if len(text.strip()) < 200:
        issues.append("HTML çıktısı çok kısa; derleme eksik olabilir")
    if "{{" in text and "}}" in text:
        issues.append("Şablon yer tutucusu derlenmemiş ({{...}} kaldı)")
    if verbose and issues:
        for iss in issues:
            print(f"[html] {iss}")
    return issues
