"""Kalite taraması: yasaklı AI kalıpları, uzun cümleler, bağlaç tekrarları."""

from __future__ import annotations

import os
import re
from pathlib import Path

from makale_pipeline import DOCUMENTS_DIR, PROJECT_ROOT
from makale_pipeline.humanizer import scan_humanizer

BANNED_PHRASES = [
    "oldukça",
    "büyük ölçüde",
    "önemli ölçüde",
    "nitekim",
    "zira",
    "şöyle ki",
    "söz konusu",
    "bir başka ifadeyle",
    "diğer taraftan",
    "bununla birlikte",
    "sebepler vardır",
    "mümkündür ki",
    "söz konusudur ki",
    "teşkil etmek",
    "bir dönüm noktası",
    "mazhar olmak",
    "önem arz etmek",
    "ifa etmek",
    "belirtildiği üzere",
    "belirtildiği gibi",
    "esas itibarıyla",
    "kanaatine göre",
    "daha önce de belirtildiği",
]

PASSIVE_SUFFIX_RE = re.compile(r"[aeıioöuü]n(mak|ma)|[aeıioöuü]l(mak|ma)", re.IGNORECASE)

DIR_SUFFIX_RE = re.compile(r"\b\w+[dDtT][ıiİİ][rR]\b")

CONJUNCTIONS = {
    "ancak", "fakat", "çünkü", "bu nedenle", "bu sebeple",
    "dolayısıyla", "üstelik", "dahası", "bununla birlikte",
    "yine de", "böylece", "nitekim", "zira", "ayrıca",
}

LONG_SENTENCE_THRESHOLD = 45


def _line_of(text: str, pos: int) -> int:
    return text[:pos].count("\n") + 1 if pos >= 0 else 0


def scan_text(text: str, file_name: str = "") -> list[dict]:
    """Metindeki kalite sorunlarını (dict listesi) döndürür."""
    issues: list[dict] = []

    for phrase in BANNED_PHRASES:
        pattern = re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE)
        for m in pattern.finditer(text):
            issues.append({
                "type": "yasakli_ifade",
                "severity": "uyari",
                "line": _line_of(text, m.start()),
                "message": f"Yasakli ifade: '{m.group()}'",
            })

    sentences = list(re.finditer(r"[^.!?\n]+[.!?]*", text))
    for m in sentences:
        sent = m.group().strip()
        words = sent.split()
        if len(words) > LONG_SENTENCE_THRESHOLD:
            preview = " ".join(words[:10]) + "..."
            issues.append({
                "type": "uzun_cumle",
                "severity": "uyari",
                "line": _line_of(text, m.start()),
                "message": f"Uzun cumle ({len(words)} kelime): '{preview}'",
            })

    dir_matches = DIR_SUFFIX_RE.findall(text)
    total_sentences = max(len(sentences), 1)
    if dir_matches:
        ratio = len(dir_matches) / total_sentences
        if ratio > 0.6:
            issues.append({
                "type": "sik_dir_eki",
                "severity": "bilgi",
                "line": 0,
                "message": (
                    f"-dir/-dir eki sik kullanilmis "
                    f"(cumle basina {ratio:.1f}, {len(dir_matches)} kez)"
                ),
            })

    paragraphs = text.split("\n\n")
    for pi, para in enumerate(paragraphs):
        found_conjs = {}
        for conj in CONJUNCTIONS:
            count = len(re.findall(re.escape(conj), para, re.IGNORECASE))
            if count > 0:
                found_conjs[conj] = count
        for conj, count in found_conjs.items():
            if count > 1:
                pos = text.find(para[:30])
                issues.append({
                    "type": "tekrarlayan_baglac",
                    "severity": "bilgi",
                    "line": _line_of(text, pos) if pos >= 0 else 0,
                    "message": f"Baglac tekrari: '{conj}' {count} kez (paragraf {pi + 1})",
                })

    # Humanizer sinyal taraması: yapısal AI izleri (akademik register'a uygun olanlar)
    issues.extend(scan_humanizer(text))

    return issues


def scan_file(tr_path: Path) -> list[dict]:
    if not tr_path.exists():
        return [{"type": "hata", "severity": "hata", "line": 0, "message": f"Dosya yok: {tr_path}"}]

    text = tr_path.read_text(encoding="utf-8")
    return scan_text(text, tr_path.name)


def scan_all(docs_dir: Path | None = None) -> dict[str, list[dict]]:
    """Tüm *_tr.txt dosyalarını tarar (taslaklar hariç)."""
    docs_dir = docs_dir or DOCUMENTS_DIR
    results: dict[str, list[dict]] = {}
    if not docs_dir.is_dir():
        return results
    for root, _, files in os.walk(docs_dir):
        p = Path(root)
        for file in files:
            if file.endswith("_tr.txt") and not file.endswith("_tr_draft.txt"):
                tr_file = p / file
                rel = tr_file.relative_to(PROJECT_ROOT)
                results[str(rel)] = scan_file(tr_file)
    return results
