"""makale_pipeline — akademik makale çeviri ve derleme paketi.

Çeviri işlemi IDE içindeki AI asistanı tarafından yapılır; bu paket prompt
üretimi, doğrulama, kalite kontrolü ve derleme sağlar. Harici çeviri
API'si veya kütüphanesi kullanılmaz.

Birincil derleme çıktısı makale formatında Word (.docx); HTML derleme
config ile kapatılabilir (`output_formats`).
"""

from __future__ import annotations

from pathlib import Path

__version__ = "5.1.0"

# src/makale_pipeline/__init__.py -> src -> proje kökü
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DOCUMENTS_DIR = PROJECT_ROOT / "documents"
TEMPLATE_FILE = PROJECT_ROOT / "templates" / "template.html"
INCOMING_DIR = PROJECT_ROOT / "incoming"
SCRATCH_DIR = PROJECT_ROOT / "scratch"

__all__ = [
    "__version__",
    "PROJECT_ROOT",
    "DOCUMENTS_DIR",
    "TEMPLATE_FILE",
    "INCOMING_DIR",
    "SCRATCH_DIR",
]
