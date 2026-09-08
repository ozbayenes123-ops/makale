"""DOCX -> PDF: Word COM otomasyonu (birincil), LibreOffice yedeği."""

from __future__ import annotations

import shutil
from pathlib import Path

PDF_FORMAT = 17  # wdExportFormatPDF


def _via_word(src: Path, out: Path) -> None:
    import win32com.client  # type: ignore

    word = win32com.client.DispatchEx("Word.Application")
    try:
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(src))
        try:
            doc.SaveAs(str(out), FileFormat=PDF_FORMAT)
        finally:
            doc.Close(False)
    finally:
        word.Quit()


def _via_libreoffice(src: Path, out: Path) -> None:
    import subprocess

    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    if not soffice:
        raise RuntimeError("LibreOffice bulunamadı (soffice yok)")
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir",
         str(out.parent), str(src)],
        check=True, capture_output=True, timeout=300,
    )
    produced = out.parent / (src.stem + ".pdf")
    if produced != out and produced.exists():
        produced.replace(out)


def export_pdf(docx_path: Path | str, output_path: Path | str | None = None,
               engine: str = "auto") -> dict:
    """Derlenmiş .docx dosyasını PDF'e çevirir (Word gerektirir)."""
    src = Path(docx_path)
    if not src.exists():
        raise FileNotFoundError(f"DOCX yok: {src}")
    out = Path(output_path) if output_path else src.with_suffix(".pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    used = ""
    errors: list[str] = []
    for cand in ([engine] if engine != "auto" else ["word", "libreoffice"]):
        try:
            if cand == "word":
                _via_word(src, out)
            else:
                _via_libreoffice(src, out)
            used = cand
            break
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{cand}: {exc}")
    if not used:
        raise RuntimeError("PDF üretilemedi: " + " | ".join(errors))
    return {"source": str(src), "output": str(out), "engine": used,
            "bytes": out.stat().st_size}
