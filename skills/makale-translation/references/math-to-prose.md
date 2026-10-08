# Math-to-Prose Rewrite Recipe

For makale translations where the user wants formulas removed and the article re-framed as social-sciences prose.

## Decision Table

| Source line | Action | Example |
|---|---|---|
| Pure equation / symbol run | Replace with one verbal sentence | `p751: sermaye payi otomasyon duzeyi ile artar.` |
| Proposition / Lemma / Proof header | Keep pN, render as finding | `p1757: Modelin bu noktadaki ongorusu sudur: ...` |
| Figure/table numbers | Verbalize trend, keep values | `pay yuzde ... duzeyinden ... duzeyine yukselir` |
| Appendix proofs (hundreds of lines) | Summarize per ~50-para block + short placeholder per pN | `p1753: [Bu ispatin sozel karsiligi: ...]` |
| Narrative argument | Normal sense-first translation | - |

## Full-Rewrite Variant

- Goal is finished prose, not coverage: merge line-split fragments into 4–8-sentence paragraphs under real subsections; renumber p1…pN in the assembled file.
- Banned in this mode: equation/symbol runs, meta-placeholders (`[Ispat adimi...]`, `bu satir ... etiketidir`, `bu ifade denklem numarasini tasir`), unfinished sentences carried over from the draft.
- Keep the argument arc, key quotes with attributions (Lee, Ma, Hanauer, Marx), load-bearing numbers (years, JEL, grant IDs); condense the bibliography to 15–20 key entries.

## Rules

- Keep every pN number; output one line per pN, never merge or drop.
- Keep numbers, years, percents, JEL codes, grant IDs (e.g. 223K672), names, citations (Lee 2022, Marx 1867).
- Gap-fill only from adjacent sentences; introduce no new thesis, result, or citation.
- Forbidden: oldukca, nitekim, zira, soz konusu, teskil etmek, buyuk olcude; repetitive ayrica/ancak/boylece chains; parenthesized English originals.
- Prefer finite verbs over nominalizations; vary sentence openings.
