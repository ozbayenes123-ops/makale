"""Yerel OCR (EasyOCR): taranmış PDF/görüntü -> metin.

easyocr kurulu değilse açık hata verir (pip install "makale-pipeline[ocr]").
"""

from __future__ import annotations

from pathlib import Path


def ocr_available() -> bool:
    try:
        import easyocr  # noqa: F401
    except ImportError:
        return False
    return True


def ocr_health() -> dict:
    ok = ocr_available()
    info: dict = {"backend": "local", "available": ok}
    if ok:
        try:
            import easyocr

            info["version"] = getattr(easyocr, "__version__", "?")
        except ImportError:
            info["available"] = False
    else:
        info["hint"] = 'pip install "makale-pipeline[ocr]" (easyocr)'
    return info


def ocr_pages(path: Path | str, langs: list[str] | None = None) -> dict:
    try:
        import easyocr
    except ImportError as exc:
        raise RuntimeError('Yerel OCR için easyocr gerekli: pip install "makale-pipeline[ocr]"') from exc
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(f"Dosya yok: {src}")
    reader = easyocr.Reader(list(langs or ["tr", "en"]), gpu=False)
    if src.suffix.lower() == ".pdf":
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("PDF sayfaları için PyMuPDF gerekli") from exc
        pages_text: list[str] = []
        with fitz.open(str(src)) as doc:
            for i, page in enumerate(doc):
                pix = page.get_pixmap(dpi=200)
                result = reader.readtext(pix.samples, detail=0)
                pages_text.append("\n".join(result))
        text = "\n\n".join(pages_text)
        return {"source": str(src), "pages": len(pages_text), "chars": len(text), "text": text}
    result = reader.readtext(str(src), detail=0)
    text = "\n".join(result)
    return {"source": str(src), "pages": 1, "chars": len(text), "text": text}
