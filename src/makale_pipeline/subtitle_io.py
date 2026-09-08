"""Altyazı (SRT) okuma/yazma: zaman damgaları korunarak çeviri hattı.

read: SRT -> L<n>: metin listesi (+ zaman haritası JSON).
write: çevrilmiş L<n> satırları + harita -> yeni SRT.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SRT_BLOCK_RE = re.compile(
    r"(\d+)\s*\n(\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3})\s*\n(.*?)(?=\n\d+\s*\n\d{2}:|\Z)",
    re.DOTALL,
)


def parse_srt(text: str) -> list[dict]:
    blocks = []
    for m in SRT_BLOCK_RE.finditer(text):
        body = m.group(3).strip().replace("\n", " ")
        body = re.sub(r"\s+", " ", body)
        blocks.append({"n": int(m.group(1)), "stamp": m.group(2).strip(), "text": body})
    return blocks


def subtitle_read(
    source_path: Path | str, map_path: Path | str | None = None
) -> dict:
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"SRT bulunamadı: {src}")
    blocks = parse_srt(src.read_text(encoding="utf-8-sig"))
    numbered = "\n".join(f"L{b['n']}: {b['text']}" for b in blocks)
    out_map = Path(map_path) if map_path else src.with_suffix(".map.json")
    out_map.write_text(
        json.dumps(
            {"source": str(src), "stamps": {b["n"]: b["stamp"] for b in blocks}},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    return {
        "source": str(src),
        "map": str(out_map),
        "lines": len(blocks),
        "numbered_text": numbered,
    }


def subtitle_write(
    source_path: Path | str,
    map_path: Path | str,
    lines: list[str] | str,
    output_path: Path | str | None = None,
) -> dict:
    mp = json.loads(Path(map_path).read_text(encoding="utf-8"))
    stamps = {int(k): v for k, v in mp.get("stamps", {}).items()}
    if isinstance(lines, str):
        items: dict[int, str] = {}
        for ln in lines.splitlines():
            m = re.match(r"^L(\d+)\s*:\s*(.*)$", ln.strip())
            if m:
                items[int(m.group(1))] = m.group(2).strip()
    else:
        items = {i + 1: t for i, t in enumerate(lines)}
    out_lines = []
    for n in sorted(set(stamps) | set(items)):
        stamp = stamps.get(n, "00:00:00,000 --> 00:00:00,000")
        out_lines += [str(n), stamp, items.get(n, ""), ""]
    out = Path(output_path) if output_path else Path(source_path).with_suffix(".tr.srt")
    out.write_text("\n".join(out_lines), encoding="utf-8")
    return {"source": str(source_path), "output": str(out), "lines": len(stamps)}
