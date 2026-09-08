"""Humanizer sinyal taraması: akademik sicile uyan yapısal AI izleri.

Yasaklı kelime listesi quality.py'dedir; burası cümle/ritim düzeyindeki
tekrar kalıplarını yakalar: aynı cümle başı zincirleri, tire/ünlem
aşırılığı, kalıp kapanışlar, ikinci şahıs kaymaları.
"""

from __future__ import annotations

import re

MAX_SAME_STARTER = 3

CLOSING_CLICHES = [
    "genel olarak bakıldığında",
    "tüm bunlar göz önüne alındığında",
]

SECOND_PERSON_RE = re.compile(
    r"(?<!\w)(sen|siz|sizin|senin|bakınız|bkz\.?|dikkat edin)(?!\w)",
    re.IGNORECASE,
)


def _line_of(text: str, pos: int) -> int:
    return text[:pos].count("\n") + 1 if pos >= 0 else 0


def _sentences(text: str) -> list[tuple[int, str]]:
    out = []
    for m in re.finditer(r"[^.!?\n]+[.!?]?", text):
        sent = m.group().strip()
        if sent and len(sent.split()) >= 3:
            out.append((m.start(), sent))
    return out


def scan_humanizer(text: str) -> list[dict]:
    issues: list[dict] = []
    sents = _sentences(text)

    # Aynı kelimeyle başlayan art arda cümleler
    run_word: str | None = None
    run_len = 0
    run_pos = 0
    for pos, sent in sents:
        first = sent.split()[0].strip(",;:\"'\"'()").lower()
        if first == run_word:
            run_len += 1
        else:
            if run_len >= MAX_SAME_STARTER and run_word:
                issues.append({
                    "type": "tekrarli_cumle_basi",
                    "severity": "bilgi",
                    "line": _line_of(text, run_pos),
                    "message": f"Art arda {run_len} cümle '{run_word}' ile başlıyor",
                })
            run_word = first
            run_len = 1
            run_pos = pos
    if run_len >= MAX_SAME_STARTER and run_word:
        issues.append({
            "type": "tekrarli_cumle_basi",
            "severity": "bilgi",
            "line": _line_of(text, run_pos),
            "message": f"Art arda {run_len} cümle '{run_word}' ile başlıyor",
        })

    # Tire/ünlem/üç nokta aşırılığı
    total = max(len(sents), 1)
    for char, label in (("—", "uzun tire"), ("–", "kısa tire"), ("!", "ünlem"), ("...", "üç nokta")):
        count = text.count(char)
        if count and count / total > 0.5:
            issues.append({
                "type": "noktalama_asiri",
                "severity": "bilgi",
                "line": 0,
                "message": f"'{label}' sık kullanılmış ({count} kez, {len(sents)} cümlede)",
            })

    # Kalıp kapanışlar
    for clich in CLOSING_CLICHES:
        for m in re.finditer(r"(?<!\w)" + re.escape(clich) + r"(?!\w)", text, re.IGNORECASE):
            issues.append({
                "type": "kalip_kapanis",
                "severity": "bilgi",
                "line": _line_of(text, m.start()),
                "message": f"Kalıp kapanış ifadesi: '{m.group()}'",
            })

    # İkinci şahıs kayması (akademik metinde nadirdir)
    for m in SECOND_PERSON_RE.finditer(text):
        issues.append({
            "type": "ikinci_sahis",
            "severity": "bilgi",
            "line": _line_of(text, m.start()),
            "message": f"İkinci şahıs kullanımı: '{m.group()}'",
        })

    return issues
