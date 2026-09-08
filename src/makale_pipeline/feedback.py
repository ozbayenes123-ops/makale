# -*- coding: utf-8 -*-
"""Word geri bildirimi: izlenen değişiklikler + yorumları okur.

Hoca/editör DOCX üzerinde düzeltme yaptıysa, bu modül ekleme/silme ve
yorumları çıkarıp _tr.txt'ye işlenmek üzere raporlar (uygulama ajan işidir).
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _text_of(el) -> str:
    return "".join(t.text or "" for t in el.iter(f"{_W}t")).strip()


def _para_text_before(paras_xml, target) -> str:
    for p in paras_xml:
        if target in list(p.iter()):
            return _text_of(p)[:160]
    return ""


def read_feedback(docx_path: Path | str) -> dict:
    src = Path(docx_path)
    if not src.exists():
        return {"ok": False, "error": f"DOCX yok: {src}"}
    try:
        zf = zipfile.ZipFile(src)
        doc_root = ElementTree.fromstring(zf.read("word/document.xml"))
        try:
            cmt_root = ElementTree.fromstring(zf.read("word/comments.xml"))
        except KeyError:
            cmt_root = None
    except (OSError, ElementTree.ParseError) as exc:
        return {"ok": False, "error": f"DOCX okunamadı: {exc}"}

    paras = list(doc_root.iter(f"{_W}p"))
    insertions, deletions = [], []
    for ins in doc_root.iter(f"{_W}ins"):
        insertions.append({
            "author": ins.get(f"{_W}author", "?"),
            "date": (ins.get(f"{_W}date", "") or "")[:10],
            "text": _text_of(ins)[:300],
        })
    for dele in doc_root.iter(f"{_W}del"):
        deletions.append({
            "author": dele.get(f"{_W}author", "?"),
            "date": (dele.get(f"{_W}date", "") or "")[:10],
            "text": _text_of(dele)[:300],
        })

    comments = []
    if cmt_root is not None:
        bodies = {c.get(f"{_W}id"): c for c in cmt_root.findall(f"{_W}comment")}
        starts: dict[str, object] = {}
        for p in paras:
            for rs in p.iter(f"{_W}commentRangeStart"):
                cid = rs.get(f"{_W}id")
                if cid:
                    starts[cid] = p
        for cid, c in bodies.items():
            author = c.get(f"{_W}author", "?")
            date = (c.get(f"{_W}date", "") or "")[:10]
            text = " ".join(_text_of(p) for p in c.findall(f"{_W}p"))[:500]
            ctx_el = starts.get(cid)
            ctx = _text_of(ctx_el)[:160] if ctx_el is not None else ""
            comments.append({"author": author, "date": date,
                             "context": ctx, "comment": text})

    total = len(insertions) + len(deletions) + len(comments)
    return {"ok": True, "source": src.name, "insertions": insertions,
            "deletions": deletions, "comments": comments, "total": total}
