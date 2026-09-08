"""Web'den makale çekme: URL -> ham metin dosyası (taslak hattına giriş)."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path


def fetch_article(url: str, output_path: Path | str | None = None) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "makale-pipeline/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
    text = raw.decode(charset, errors="ignore")
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        title = (soup.title.string or "").strip() if soup.title else ""
        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        paras = [p for p in paras if len(p.split()) > 3]
        body = "\n\n".join(paras)
    except ImportError:
        title = ""
        body = re.sub(r"<[^>]+>", " ", text)
        body = re.sub(r"\s+", " ", body).strip()

    draft = (f"[TITLE]\n{title}\n[/TITLE]\n\n[BODY]\n{body}\n[/BODY]\n" if title
             else f"[BODY]\n{body}\n[/BODY]\n")
    out = Path(output_path) if output_path else Path("incoming") / "fetched.draft.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(draft, encoding="utf-8")
    return {"url": url, "output": str(out), "chars": len(draft), "title": title}
