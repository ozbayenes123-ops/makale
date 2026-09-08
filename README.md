# makale-pipeline v5

Akademik makale çeviri ve derleme sistemi (IDE tabanlı AI destekli) + MCP sunucusu.

- Çeviriyi AI asistanı yapar (`makale prep` prompt üretir, `makale apply` doğrular).
- **Birincil çıktı: makale formatında Word (.docx)** — A4, Times New Roman 12,
  iki yana yaslı, 1.5 satır, gerçek Word dipnotları, içindekiler, sayfa no.
- HTML derleme ikincil (`config.json` → `output_formats: ["docx", "html"]`).
- Çeviri QA: sayı/tarih/yüzde korunumu, özel ad/kısaltma takibi, paragraf
  hizalı sözlük denetimi (`translation_qa.py`, `validate.py`, `semantics.py`).

## Kurulum

```bash
uv sync --project C:\dev\mcp\makale
```

## CLI

```bash
makale status            # belge durum tablosu
makale prep <kaynak>     # çeviri promptu üret
makale apply <kaynak>    # doğrula + Word derle
makale validate [kaynak] # kaynak/hedef doğrulama
makale compile           # tüm çevirileri derle
makale semantic <kaynak> --summary
makale quality [yol]
makale glossary --show <kaynak> | --check <kaynak>
makale search <sorgu> | makale stats | makale docs | makale index
makale serve             # MCP sunucusu (stdio)
```

## MCP

```bash
uv run --project C:\dev\mcp\makale makale serve
```

24 araç: doc_status, ocr_health, ocr_document, translate_prep/apply,
write_translation, validate_document/all, compile_all/document, build_index,
search, quality_scan, glossary_check/show, semantic_check, project_stats,
read_document, extract_pdf, read_docx, export_docx, subtitle_read/write,
fetch_article.

## Word biçimi ayarı

Belge `config.json` içine `docx` bölümü:

```json
{
  "output_formats": ["docx"],
  "docx": {
    "body_size_pt": 12,
    "line_spacing": 1.5,
    "first_line_indent_cm": 1.25,
    "page_numbers": true,
    "toc": true
  }
}
```

Tüm anahtarlar için `src/makale_pipeline/config.py` → `DEFAULT_DOCX`.
