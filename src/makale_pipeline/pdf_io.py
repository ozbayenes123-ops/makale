"""PDF metin çıkarma (PyMuPDF): dijital PDF -> ham taslak TXT."""

from __future__ import annotations

import re
from pathlib import Path


def extract_pdf(source_path: Path | str, output_path: Path | str | None = None) -> dict:
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"PDF bulunamadı: {src}")
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF kurulu değil (pip install PyMuPDF)") from exc

    chunks: list[str] = []
    pages = 0
    with fitz.open(str(src)) as doc:
        pages = len(doc)
        for page in doc:
            text = page.get_text("text") or ""
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            if text:
                chunks.append(text)

    draft = "\n\n".join(chunks)
    out = Path(output_path) if output_path else src.with_suffix(".draft.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(draft, encoding="utf-8")
    return {
        "source": str(src),
        "output": str(out),
        "pages": pages,
        "chars": len(draft),
        "nonempty_pages": len(chunks),
    }
