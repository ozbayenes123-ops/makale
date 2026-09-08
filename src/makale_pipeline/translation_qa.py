"""Çeviri QA: sayı/veri korunumu ve sözlük (glossary) kapsaması.

Çevirinin kendisi AI asistanı tarafından üretilir; bu modül üretilen
hedefin kaynaktaki somut birimleri (sayı, tarih, yüzde, ölçü, kısaltma,
özel isim adayı) aynen taşıyıp taşımadığını ve sözlük karşılıklarının
uygulanıp uygulanmadığını denetler.
"""

from __future__ import annotations

import re
from collections import Counter

MAX_EXAMPLES = 8

_DIGIT_RUN_RE = re.compile(r"\d+")
_ACRONYM_RE = re.compile(r"\b[A-ZÇĞİÖŞÜ]{2,}[A-ZÇĞİÖŞÜ'’.-]*")


def _digit_runs(text: str) -> Counter:
    return Counter(_DIGIT_RUN_RE.findall(text))


def check_numeric_coverage(source, target) -> list[str]:
    """Kaynaktaki her sayı dizisi hedefte de geçmeli (sıra bağımsız, adetli)."""
    warnings: list[str] = []
    src_runs = _digit_runs(source.body_text())
    if not src_runs:
        return warnings
    tr_runs = _digit_runs(target.body_text())
    missing = (src_runs - tr_runs)
    if not missing:
        return warnings
    examples = list(missing.elements())[:MAX_EXAMPLES]
    rest = sum(missing.values()) - len(examples)
    msg = f"Kaynaktaki sayı dizileri hedefte eksik: {examples}"
    if rest > 0:
        msg += f" (+{rest} tane daha)"
    warnings.append(msg + " — sayı/tarih/yüzde atlanmış olabilir")
    return warnings


def _acronyms(text: str) -> Counter:
    found = [m.group(0).strip(".-") for m in _ACRONYM_RE.finditer(text)]
    return Counter(f for f in found if len(f) >= 2)


def _capitalized_frequent(text: str, min_freq: int = 2) -> Counter:
    words = re.findall(r"[A-Za-zÇçĞğİıÖöŞşÜü'’\-]+", text)
    cap = [w for w in words if w and w[0].isupper() and len(w) > 1]
    return Counter(w for w, c in Counter(cap).items() if c >= min_freq)


def check_proper_noun_coverage(source, target, glossary: dict | None = None) -> list[str]:
    """Kısaltmalar ve sık geçen büyük harfli adaylar hedefte korunmalı.

    Sözlükte karşılığı tanımlı terimler bu kontrolden muaftır (onlar
    check_glossary_coverage ile denetlenir).
    """
    warnings: list[str] = []
    glossary = glossary or {}
    gloss_keys = {str(k).lower() for k in glossary}
    src_text = source.body_text()
    tr_text = target.body_text()

    src_acr = _acronyms(src_text)
    tr_acr = _acronyms(tr_text)
    missing_acr = (src_acr - tr_acr)
    shown = 0
    for token in list(missing_acr.elements()):
        if shown >= MAX_EXAMPLES:
            break
        if token.lower() in gloss_keys:
            continue
        warnings.append(f"Kısaltma/özel ad hedefte yok: '{token}'")
        shown += 1

    src_cap = _capitalized_frequent(src_text)
    shown = 0
    for token in src_cap:
        if shown >= MAX_EXAMPLES:
            break
        if token.lower() in gloss_keys:
            continue
        if token in tr_text:
            continue
        # Tekil iyelik/çekim varyantı hedefte olabilir ("Hodgson'un" gibi).
        if re.search(r"(?<!\w)" + re.escape(token) + r"\w*", tr_text):
            continue
        warnings.append(f"Özel ad adayı hedefte geçmiyor: '{token}'")
        shown += 1
    return warnings


def _align_paragraphs(src_paras: list[str], tr_paras: list[str]) -> list[tuple[int, int]]:
    """Kaynak/hedef paragrafları hizalar (sayılar eşit değilse difflib ile).

    Dönen: [(src_idx, tr_idx)] — eşleşemeyen kaynak paragrafı tr_idx=-1 alır.
    """
    import difflib

    if len(src_paras) == len(tr_paras):
        return list(zip(range(len(src_paras)), range(len(tr_paras))))
    if not src_paras or not tr_paras:
        return [(i, -1) for i in range(len(src_paras))]
    sm = difflib.SequenceMatcher(a=None, b=None, autojunk=False)
    # Karşılaştırma anahtarı: sayılar + ilk kelimeler (dilden bağımsız iskelet).
    key = lambda p: (tuple(_DIGIT_RUN_RE.findall(p)), tuple(p.split()[:4]))
    sm.set_seqs([key(p) for p in src_paras], [key(p) for p in tr_paras])
    pairs: list[tuple[int, int]] = []
    used_tr: set[int] = set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                pairs.append((i, j))
                used_tr.add(j)
        else:
            free = [j for j in range(j1, j2) if j not in used_tr]
            for k, i in enumerate(range(i1, i2)):
                j = free[k] if k < len(free) else -1
                pairs.append((i, j))
                if j >= 0:
                    used_tr.add(j)
    return sorted(pairs)


def check_glossary_coverage(source, target, glossary: dict | None = None) -> list[str]:
    """Sözlükteki her kaynak terim hedefte karşılığıyla geçmeli.

    Paragraf hizalı denetim: terimin geçtiği kaynak paragraf sırasındaki
    hedef paragrafta karşılık aranır; sıra kayması uyarı üretir.
    """
    warnings: list[str] = []
    glossary = glossary or {}
    if not glossary:
        return warnings

    src_paras = [p.text for s in source.sections for p in s.paragraphs]
    tr_paras = [p.text for s in target.sections for p in s.paragraphs]
    aligned = _align_paragraphs(src_paras, tr_paras)
    tr_by_src = {i: j for i, j in aligned}

    for en_term, tr_term in glossary.items():
        en_term = str(en_term)
        tr_term = str(tr_term)
        if not en_term.strip() or not tr_term.strip():
            continue
        en_pat = re.compile(r"(?<!\w)" + re.escape(en_term) + r"(?!\w)", re.IGNORECASE)
        tr_pat = re.compile(r"(?<!\w)" + re.escape(tr_term) + r"(?!\w)", re.IGNORECASE)
        hit_src = [i for i, p in enumerate(src_paras) if en_pat.search(p)]
        if not hit_src:
            continue
        bad = [
            i + 1 for i in hit_src
            if tr_by_src.get(i, -1) < 0 or not tr_pat.search(tr_paras[tr_by_src[i]])
        ]
        if bad:
            shown = bad[:5]
            extra = f" (+{len(bad) - len(shown)} paragraf daha)" if len(bad) > len(shown) else ""
            warnings.append(
                f"Sözlük karşılığı eksik: '{en_term}' -> '{tr_term}' "
                f"(kaynak paragraf {shown}{extra})"
            )
    return warnings
