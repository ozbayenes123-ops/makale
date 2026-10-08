# DergiPark Recommendations from Translated Corpus

When the user asks for DergiPark reading suggestions based on what makale has translated so far, profile the corpus first, then search DergiPark by derived Turkish keywords.

## 1. Profile the corpus on disk, not only via MCP

- List on-disk state first: `ls "C:/dev/mcp/makale/documents"` then per-slug `ls "C:/dev/mcp/makale/documents/<slug>"`. `doc_status` undercounts — unregistered targets (e.g. standalone `sosyal_tr.txt`) and `scratch/part*_tr.txt` / `scratch/sosyal_*.txt` do not appear in it.
- Identify the source: read the first 80-120 lines of `<base>_en.txt` (or `*_tr.txt`) with `read_file`. Extract title, authors, date, Keywords/JEL line, and the abstract (`p1-p3`). Derive 3-4 Turkish theme clusters from it (e.g. otomasyon+gorev modeli, sermaye-emek payi+esitsizlik, yeniden dagitim vs baski, demokrasi/darbe).
- Do NOT rely on `read_document` with the slug alone — it fails with `No such file` when given a folder path. Read the concrete `documents/<slug>/<file>.txt` path instead.

## 2. Search DergiPark

- Run 2-3 parallel `web_search` queries with `site:dergipark.org.tr` using Turkish keyword pairs, one per theme cluster (e.g. `otomasyon yapay zeka emek piyasasi esitsizlik`, `evrensel temel gelir yeniden dagitim`, `demokrasi gelir dagilimi`). One backend may 403 while another succeeds — treat a single failure as transient and use the results that returned.
- Cite the landing page `dergipark.org.tr/tr/pub/.../article/...`, never the `/tr/download/article-file/...` PDF link. Verify the top 2-3 hits with `web_extract` to confirm clean title, journal, year, and DOI before recommending.

## 3. Present grouped, in reading order

- Group by theme mapping back to the source paper (e.g. yeniden dagitim tarafi, teknolojik issizlik zemini, demokrasi/kurumlar tarafi). One line per item: full citation + landing URL + why it connects to the translated work.
- Give an explicit reading order (shortest/most accessible Turkish article first). Offer to `fetch_article` one pick into makale as the next step; do not import automatically.

## 4. Zotero-profiled diverse recommendations

- When the user asks for suggestions from their Zotero library plus DergiPark variety, profile Zotero collections first (counts + 10-25 sample titles per major collection), derive one theme per major collection, then pick one DergiPark article per theme so each collection gets a continuation.
- Discover via `web_search` with Turkish keyword pairs; verify only `/tr/pub/.../article/...` landing pages with `web_extract` — never `web_extract` DergiPark `/tr/search` pages, they return a bot-wall (Arama Dogrulama) instead of results.
- Verify the journal code before citing a journal by spoken name — no DergiPark journal is coded `diva`; confirm whether `da` (Dini Arastirmalar) or `divan` (Divan) is meant rather than guessing.
