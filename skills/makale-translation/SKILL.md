---
name: makale-translation
description: Use when translating articles via makale MCP.
version: 1.0.0
author: Hermes Curator
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [makale, translation, academic, docx, mcp]
---

# Makale Article Translation

Class-level workflow for English→Turkish academic translation through `C:/dev/mcp/makale` (`makale serve`, 36+ tools). Primary output is makale-format DOCX.

## When to Use

- User names a source file outside makale (Desktop/incoming) and says translate with makale
- Any `documents/<slug>/` task: prep → translate → validate → compile DOCX
- Math-heavy source requested as social-sciences prose (formulas removed, meaning verbalized)

## Procedure

0. PDF sources: render only a few representative pages and `vision_analyze` them for structure (heading levels, footnote style, tables, cover/map pages) to choose the extraction plan. Do not visually inspect every page by default; use targeted vision only for pages flagged by fidelity checks or suspicious page breaks, truncated words, missing footnote anchors, and complex tables. This user's preference is selective, evidence-led vision, not a full-document image sweep.
1. Import: create `documents/<slug>/`, copy source as `<base>_en.txt` (the `_en` suffix is required for language inference). `extract_pdf` gives only a raw per-page dump — for academic PDFs with real footnotes, rebuild `[TITLE]/[BODY]/pN/[fn N]/[FOOTNOTES]` structure with pymupdf per `references/pdf-layout-to-structured.md` and set `source_layout_extraction: true` in the folder's `config.json`. Confirm with `doc_status` (`structured:true`, `pending_translations:1`). Before translating, run the fidelity audit from `references/pdf-layout-to-structured.md` 'Fidelity audit after extraction': use text/structure checks to flag likely omissions first, then compare only flagged OCR pages/regions against rendered images; for clean text-layer PDFs use exact full-string coverage. Treat confirmed OCR loss as a defect: repair the source and retranslate affected items before shipping.
2. Map: run `chunk_translate` (note `parts`, `total_chars`, paragraph count) and `glossary_extract` (top 40) before writing any Turkish. Its result often spills to a cache file — parse the FIRST line of the spill file with `json.loads` (later lines are mcp metadata and break plain parsing), then write each part's `prompt` string to `scratch/prompt_<part>.txt` and hand children those files instead of pasting prompts.
3. Translate: keep strict `pN:` 1:1 numbering — never skip, merge, or renumber. Long docs (>1000 paras or line-split PDFs with thousands of `pN`) go in parallel ranges to `scratch/partN_tr.txt`, then concatenate to `<base>_tr.txt`. Size ranges by OUTPUT volume, not paragraph count: short line-split lines tolerate 150–225 paras/range, but full academic paragraphs plus their footnote definitions cap at ~15 paragraphs or ~30 footnotes per child — a bigger unit exhausts the child's output-token budget and dies as 'Response remained truncated after N continuation attempts' with no file written, wasting the whole run. Split body paragraphs and footnote definitions into SEPARATE child units (footnote chunks carry only their own `N:` lines). When re-dispatching a truncated range, halve it and tell the child to output nothing but the file. Tell children to locate source ranges with terminal `grep -n '^pN:'` + `sed -n` (never `execute_code read_file` on the full file; it returns empty on large line-split docs) and to write the part file before summarizing. Translate the `[TITLE]`/`[SUBSECTION title=…]`/`[SECTION title=…]` title values into Turkish inside the TR file — the pipeline renders tag values verbatim, so untranslated tags land English headings in a Turkish DOCX. If a delivered DOCX nonetheless ships English headings, repair without retranslating: rewrite the tag title values in the existing `<base>_tr.txt`, re-run `export_docx`, then assert via python-docx that every Heading 1/2 paragraph is Turkish.
4. Verify with new tools in order: `translate_diff` (expect missing 0 / extra 0) → `validate_document` → `quality_scan` → apply only scoped, meaning-preserving `quality_fix` changes; do not run broad `apply_safe` cleanup when warnings span untouched content or include legitimate citation/heading fragments, because it can silently rewrite beyond the requested scope. Then run `translate_apply` (validates AND compiles the DOCX itself — its result carries the `docx` path, so a separate `export_docx` is only needed for re-exports) → `bibliography` when footnotes exist. Report unresolved validator/quality warnings plainly rather than treating successful compilation as a clean validation. When the user suspects body text migrated into footnotes (or the reverse), settle it before editing: compare TR/EN length ratios per `pN` and per footnote (healthy band ≈0.5–2.2) and match each TR footnote to its EN footnote first — a TR footnote mirroring its EN footnote is source structure, not displacement.
5. Report: what changed, verification output, what remains — in Turkish, matching the ask length.

## Math-to-Prose Adaptation (see `references/math-to-prose.md`)

- Never copy formula/symbol runs into Turkish; write the verbal claim instead.
- Preserve every number, year, percent, measure, proper name, and citation exactly.
- Fill line-split gaps from adjacent context only; add no new claims, paragraphs, or emphasis.
- Natural academic Turkish: ban `oldukça, nitekim, zira, söz konusu, teşkil etmek` and sentence-initial conjunction chains.

## Full-Rewrite Mode (derli toplu makale)

- When the user asks for a real social-sciences article (zero formulas, proper paragraph flow, no half-sentences, wording may change), abandon 1:1 pN fidelity and rewrite section by section.
- Delegate one section per child (Ozet+Giris, Kuram, Duzenleme, Baski, Dinamik, Sonuc+secili kaynakca); each writes finished 4–8-sentence paragraphs to `scratch/sosyal_X.txt` with `##`/`###` headers. Forbid meta-talk (`bu ifade denklem numarasini tasir`, `bu satir ... etiketidir`, `[Ispat adimi...]` placeholders) and unfinished carried-over sentences.
- Assemble LINE-WISE into a standalone file (`[TITLE]`…`[/TITLE]`, `[BODY]`, `[SUBSECTION title="…"]`, renumbered `p1…pN`, `[/BODY]`) and compile with `export_docx` directly — no EN source pair is required for a standalone target.
- Finish with `quality_scan` and fix every hit before delivering.

## Main-Text-Only Rework (dipnotsuz ana metin DOCX)

When the user wants a footnote-free body-text edition (no `[fn]`, bibliography omitted), the makale export pipeline does not apply — assemble from the chunk `pN` translations with your own compile script:

1. Checkpoint discipline: when the user says 'kaldığın yeri kaydet', write a checkpoint MD under `documents/` listing file paths, completed items, and a numbered remaining-work list. On resume, re-verify every checkpoint claim with tool output (file existence, ID counts, source reads) before acting — a checkpoint is a self-report, not fact. Find lost checkpoints via `session_search` ('kaldığın yeri kaydet') plus a search of `C:/dev/mcp/makale/documents/`.
2. Load chunks with strict ID-set assertions (`assert_ids`: missing/extra/empty/`[fn]` residue all raise) and coverage counters over the full source paragraph range, including merged and split IDs (`p82a`/`p82b`).
3. Numeric audit must terminate at UNRESOLVED = 0 by classifying every digit mismatch into exactly one legitimate class — never ship with unexplained diffs, never silence the audit:
   - OCR footnote superscript glued into a word (e.g. `1992.6`, `people.10`): verify the same source paragraph carries the matching `[fn N]` right after; removal is then correct in a no-footnote edition.
   - Same digit multiset, different order: Turkish clause order — benign, record it.
   - Source spelled-out century rendered as Turkish ordinal numeral (`seventeenth century` → `17. yüzyıl`): legitimate translation, not a fabricated digit.
   - Paragraphs that are fragments of a merged quote block: audit the JOINED group (EN join vs TR join) as one unit, not per fragment. Detect stitches mechanically — a `pN` line ending without sentence punctuation followed by one starting with `(` or lowercase is a mid-sentence page break, and a paragraph opening with a bare citation (e.g. `(1982, ss. 4, 9)`) belongs to the preceding quote.
4. Duplicate table extractions: scanned tables often appear twice — once row-wise per country/entry, once column-wise smeared across paragraphs. Prove duplication by normalized comparison (lowercase, strip hyphens/spaces; expect OCR line-break artifacts like `in-dependent`, `mid- 1970s`, and a one-line country-name shift), keep one copy, drop the other only after the per-row proof. Render the kept table as a real Word table AND keep a plain-text line form in the TXT reading copy so completeness checks still pass.
5. Headings OCR-glued into paragraph text: split at the known heading string into a separate heading block and assert the remaining body starts with the expected first words — never silently guess the split point.
6. Build the DOCX from a spec JSON (blocks: heading/paragraph-with-style/table, page setup, styles) with python-docx; the makale venv has python-docx, the system python does not — run as `uv run --project C:/dev/mcp/makale python <script>.py`. Format to house style: A4, Times New Roman 12 body / 1.5 spacing, justified, bold centered title, Heading 1/2 hierarchy, PAGE field footer. Page margins come in mm — pass them through `Mm()`, never `Cm()`; a mm value routed through `Cm()` inflates 10× (25mm → 25cm) and fails only later at PDF export with a misleading 'document cannot be prepared for export' error. On tables set `w:cantSplit` per row and `w:tblHeader` on the header row so rows never break across pages and the header repeats on continuation pages.
7. Verify the finished DOCX programmatically (paragraph/heading/table counts, exact country/heading lists, zero `[fn]` markers), copy deliverables to the Desktop, and assert SHA-256 equality between source and Desktop copy before reporting done. When the user later reports a delivered file missing, re-copy and re-verify immediately instead of recounting delivery history. Programmatic green is not visual green — a unit-bug layout passes every count check while the printed page is garbage. Render the final DOCX to PDF then pymupdf→PNG at ~105dpi. When LibreOffice is absent, Word itself converts: `win32com.client.Dispatch('Word.Application')` → `Documents.Open(src, ReadOnly=True, AddToRecentFiles=False)` → `SaveAs2(dst, FileFormat=17)` (prefer `SaveAs2` over `ExportAsFixedFormat`, which rejects packages `SaveAs2` accepts) → `Quit()`; run under the makale venv (`uv run --project C:/dev/mcp/makale python`). Then vision-check the title page, one heading-transition page, and each table page (margins, overflow, style breaks, heading language) before reporting.

## Terim karşılığı bilinmiyorsa (resmî kaynak turu)

Karşılığı belirsiz/şüpheli bir terim (özellikle hukuk terimi) çıktığında tahmin
etme; sırayla başvur:

1. **Projede var mı:** `glossary_show`, `glossary_check`, `translation_memory` —
   daha önce onaylanmış karşılık varsa onu kullan.
2. **Resmî Türkçe kullanım:** bridge `terim_arastir(terim, mevzuat_ipucu=...)`.
   Araç mevzuat başlıklarını VE ilgili kanunun metnini tarar, resmî kullanım
   örneklerini döndürür. Dikkat: `mevzuat_ara` yalnızca BAŞLIK tarar; terim
   başlıkta geçmiyorsa `mevzuat_ipucu` zorunlu (ör. terim='vatansız',
   ipucu='Vatandaşlık' → yönetmelik metninden gerçek kullanım örnekleri).
3. **Yetmiyorsa web araması:** TDK/terim sözlükleri, alan literatürü, kurum
   çevirileri (mevzuat.gov.tr, resmî kurum siteleri). Kaynağı not et.
4. **Seçilen karşılığı yaz:** `glossary_add` ile sözlüğe kaynak + gerekçeyle
   ekle. Karşılıksız bırakılmış ya da uydurulmuş terim yasak; İngilizce terimin
   belgede kalması da hata sayılır.
5. **Tutarlılığı doğrula:** `glossary_check` + `quality_scan` ile belgede aynı
   terimin tek karşılıkla geçtiğini kontrol et; DOCX/PDF çıktısında kalan
   yabancı terimi kapatmadan teslim etme.

## Pitfalls

- Build the prompt with `resolve_path(PROJECT_ROOT, ...)` in mind: absolute paths outside the project break `relative_to(PROJECT_ROOT)` — always import under `documents/` first, because the prompt builder assumes project-relative paths.
- Expect `chunk_translate` to return a single part when the doc has one section even if `total_chars` far exceeds `max_chars` — split manually by `pN` ranges instead of retrying with smaller limits.
- Treat multi-thousand `pN` counts as line-split PDF extraction, not real paragraphs — compress/translate per line but keep every number for validator coverage.
- Prefer file assembly (`cp`/`cat` of part files) over `write_translation` for large targets — single-tool payloads truncate or reject hundred-KB content.
- Grep unicode-math sources as binary: add `-a` or use `sed -n` ranges, since raw `grep` reports `Binary file ... matches` and hides hits.
- Parse scratch part files line-wise (one non-empty line = one paragraph) — blank-line splitting silently merges paragraphs into their section headers and corrupts the assembly.
- Verify every `scratch/partN_tr.txt` by line count (`wc -l`) after a delegation fan-out before assembling — a child can report success while writing nothing, so re-dispatch missing or short parts in smaller ranges instead of trusting the summary.
- After merging TR parts, programmatically diff the per-paragraph `[fn N]` sequence EN vs TR — order, not just set: a child can swap two adjacent tokens while rewriting a sentence (set-equality passes, prose anchors are wrong), and only the ordered per-paragraph diff catches it. Fix with a surgical replace that moves the token to its true anchor word.
- Before applying image-audit corrections, compare each corrected paragraph's ordered `[fn N]` markers with the source; reject or manually reconcile any correction that drops or moves markers. After source edits, retranslate every changed paragraph/footnote, then verify the actual output files—not just child-agent completion claims—by checking exact expected IDs/counts and per-paragraph marker order before merging. Rerun `translate_diff`, validation, and `translate_apply`, then verify the generated DOCX exists and contains representative corrected body and footnote text, so source, translation, and artifact never silently diverge.
- For OCR fidelity, use text-layer/structure heuristics and recurring typo searches to shortlist suspects, then inspect only those regions with vision; check the adjacent page before treating a page-ending fragment as missing. When vision confirms a repeated glyph confusion (e.g. `rn`→`m`), search the full EN source for that exact token and replace only contextually valid matches; check corresponding TR lines too, especially when literal URLs or citations are preserved. If vision is unavailable or rate-limited, keep unverified proposals unapplied and report the audit as incomplete.
- After merging TR parts, sweep `validate_document` banned-phrase hits with plain string replaces in the TR file (`Bununla birlikte`→`Ne var ki`, `önemli ölçüde`→`kayda değer biçimde`, `şöyle ki`→`öyle ki`…) and re-check number coverage per paragraph before `translate_apply`; the number-QA flags a digit (e.g. `19`) the TR spelled out as words (`On dokuzuncu`) — write the numeral.
- `translate_apply` takes the EN source path and reads the sibling `<base>_tr.txt`; its `docx` field is the compiled output — rerun it after any TR edit instead of hunting for an export step.
- Run `python`, never `python3`, on this Windows host — `python3` is missing and fails silently in mixed-locale paths. pymupdf is only in the makale project env: run PDF scripts as `cd C:/dev/mcp/makale && uv run python <file>.py` with `import pymupdf`.
- Never translate the raw `extract_pdf` dump as-is: superscript footnote markers are glued onto words and footnotes are interleaved per page, so numeric QA will demand phantom digit runs — resolve markers to `[fn N]` refs first (see `references/pdf-layout-to-structured.md`).
- End every assembled `_tr.txt` with a `[/BODY]` closing line — the validator and `translate_apply` require both `[BODY]` and `[/BODY]` (`is_structured_document`), and assembly via `cat` drops the source's closing tag, failing with `Hedef yapılandırılmamış` until it is appended.

## References

- `references/math-to-prose.md` — formula-to-prose rewrite recipe + forbidden-pattern list.
- `references/dergipark-recommendations.md` — profile translated corpus on disk, then search/cite DergiPark reading suggestions.
- `references/pdf-layout-to-structured.md` — rebuild scanned/academic layout PDFs (body/footnote zone split by span size, superscript `[fn N]` recovery, OCR digit repair, table grid reconstruction) into makale structured format.

The Main-Text-Only Rework section above is self-contained; no separate reference file is needed for it.
