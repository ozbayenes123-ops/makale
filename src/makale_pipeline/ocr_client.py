"""OCR istemcisi: backend seçimi (şu an yalnızca yerel backend)."""

from __future__ import annotations

from pathlib import Path

from makale_pipeline.local_ocr import ocr_available, ocr_health, ocr_pages


def ocr_document(
    source_path: Path | str,
    backend: str = "local",
    langs: list[str] | None = None,
    output_path: Path | str | None = None,
) -> dict:
    if backend != "local":
        raise ValueError(f"Bilinmeyen OCR backend'i: {backend} (yalnızca 'local')")
    result = ocr_pages(source_path, langs=langs)
    text = result.pop("text", "")
    out = Path(output_path) if output_path else Path(result["source"]).with_suffix(".draft.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    result["output"] = str(out)
    return result


def health(backend: str = "local") -> dict:
    if backend != "local":
        return {"backend": backend, "available": False, "hint": "yalnızca 'local' desteklenir"}
    info = ocr_health()
    info["easyocr_import"] = ocr_available()
    return info
