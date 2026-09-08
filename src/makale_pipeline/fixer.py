"""Kalite otomatik düzeltme: mekanik sorunları uygular, üslup için önerir.

apply_safe=True yalnızca anlamı değiştirmeyen mekanik temizlik yapar
(çift boşluk, markdown artığı, kod çiti, noktalama boşlukları).
Yasaklı kalıplar için bağlama göre seçilecek öneriler üretilir;
otomatik değiştirilmez.
"""

from __future__ import annotations

import re
from pathlib import Path

SUGGESTIONS: dict[str, list[str]] = {
    "oldukça": ["epey", "oldukça yerine cümleyi yeniden kurun"],
    "büyük ölçüde": ["büyük oranda", "ağırlıklı olarak"],
    "önemli ölçüde": ["belirgin biçimde", "kayda değer ölçüde"],
    "nitekim": ["(silin; cümle kendi başına dursun)", "gerçekten de"],
    "zira": ["çünkü", "‐dığı için"],
    "şöyle ki": ["(silin)", "şöyle:"],
    "söz konusu": ["ilgili", "bahsedilen", "(silin)"],
    "bir başka ifadeyle": ["başka bir deyişle", "(silin)"],
    "diğer taraftan": ["öte yandan", "(silin)"],
    "bununla birlikte": ["bununla beraber (seyrek)", "(silin)"],
    "teşkil etmek": ["oluşturmak", "olmak"],
    "bir dönüm noktası": ["kırılma anı", "dönüşüm noktası"],
    "mazhar olmak": ["konusu olmak", "hedefi olmak"],
    "önem arz etmek": ["önemli olmak", "önem taşımak"],
    "ifa etmek": ["yerine getirmek"],
    "belirtildiği üzere": ["(silin)"],
    "esas itibarıyla": ["temelde", "(silin)"],
    "ayrıca": ["(gerekliyse koruyun, değilse silin)", "üstelik (seyrek)"],
}


def _mechanical(text: str) -> tuple[str, list[str]]:
    applied: list[str] = []
    new = text
    steps = [
        (r"```+\w*\n?", "", "kod çiti temizliği"),
        (r"\*\*(.+?)\*\*", r"\1", "markdown kalın artığı"),
        (r"[ \t]{2,}", " ", "çift boşluk"),
        (r" +\n", "\n", "satır sonu boşluğu"),
        (r"\n{4,}", "\n\n\n", "aşırı boş satır"),
        (r"\s+([,;:.!?])", r"\1", "noktalama öncesi boşluk"),
        (r"\(\s+", "(", "parantez içi boşluk"),
        (r"\s+\)", ")", "parantez içi boşluk"),
    ]
    for pattern, repl, label in steps:
        new2 = re.sub(pattern, repl, new)
        if new2 != new:
            applied.append(label)
            new = new2
    return new, applied


def suggest(text: str) -> list[dict]:
    """Yasaklı kalıplar için konumlu öneri listesi."""
    out: list[dict] = []
    for phrase, alts in SUGGESTIONS.items():
        pattern = re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE)
        for m in pattern.finditer(text):
            line = text[: m.start()].count("\n") + 1
            out.append({"phrase": m.group(), "line": line,
                        "alternatives": alts})
            if len(out) >= 40:
                return out
    return out


def fix_file(tr_path: Path | str, apply_safe: bool = True,
             write: bool = True) -> dict:
    p = Path(tr_path)
    if not p.exists():
        return {"ok": False, "error": f"Dosya yok: {p}"}
    text = p.read_text(encoding="utf-8")
    applied: list[str] = []
    new = text
    if apply_safe:
        new, applied = _mechanical(text)
        if write and new != text:
            p.write_text(new, encoding="utf-8")
    suggestions = suggest(new)
    return {"ok": True, "file": p.name, "applied": applied,
            "changed": new != text, "suggestions": suggestions}
