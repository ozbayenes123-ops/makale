"""Çeviri stager: prompt üretimi, uygulama (doğrula + derle) ve durum listesi.

Harici API çağrısı yapmaz. AI asistanı promptu kullanarak _tr.txt dosyasını
üretir; bu modül üretilen çeviriyi doğrular ve birincil çıktı olarak Word
(.docx) derler. HTML derleme config ile kapatılabilir.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from makale_pipeline import DOCUMENTS_DIR, PROJECT_ROOT, TEMPLATE_FILE
from makale_pipeline.compile import check_html_file, compile_document
from makale_pipeline.config import load_config
from makale_pipeline.paths import (
    find_source_files,
    infer_lang,
    resolve_path,
    target_path_for_source,
)
from makale_pipeline.structured import is_structured_document, parse_document
from makale_pipeline.validate import validate_pair

SEMANTIC_PROTOCOL = """Bu görev kelime veya cümle eşleştirme görevi değildir. Kaynak metni
önce anlam örgüsü içinde kavra, sonra Türkçe akademik metin olarak yeniden kur.

1. Çeviriye başlamadan önce kaynak belgenin tamamını ve ilgili bölümün bütününü
   oku. Başlığı, bölüm sırasını, temel kavramları, ana iddiayı ve paragraf
   ilişkilerini zihninde kur. Bu ön okuma notlarını hedef dosyaya yazma.
2. Her p<num> bloğunu tek bir anlam birimi olarak ele al. Önce paragrafın ana
   savını, kanıtını/örneğini, nitelemelerini ve sonraki paragrafa geçişini anla;
   ardından cümleleri Türkçede doğal biçimde kur.
3. Cümleleri anlamı koruyarak bölebilir veya birleştirebilirsin. Ancak paragrafın
   işlevini, sırasını, iddia-kanıt ilişkisini ve dipnot bağını bozma. Kaynakta
   olmayan yeni paragraf, yorum, sonuç veya vurgu ekleme.
4. Bağlaçları ve zamirleri mekanik olarak taşıma. Karşıtlık, neden, sonuç,
   örnekleme, sınırlama ve geçiş ilişkisini doğru kur; kaynakta olmayan bir
   ilişki kurma. Zamirlerin göndergesini gerektiğinde açıklaştır.
5. Yazarın kesinlik derecesini koru. "may", "might", "likely", "argues",
   "suggests", "must", "shall", "except" gibi kip, ihtiyat, yükümlülük ve
   istisna ifadelerini daha kesin veya daha zayıf bir hükme dönüştürme.
6. Kaynaktaki bütün önermeleri, verileri, sayıları, tarihleri, özel isimleri,
   olumsuzlukları, koşulları, alıntıları ve dipnotları koru. Paragrafı kısaltma
   veya yalnızca genel fikrini aktarma.
7. İlk taslaktan sonra iki sessiz kontrol yap: önce paragraf geçişleri, kavram
   tutarlılığı ve zamir gönderimleri; sonra kaynak-hedefteki tüm veri, iddia,
   kip ve dipnot eşleşmeleri. Analiz ve kontrol notlarını hedef dosyaya koyma.

Bu yaklaşım, projeye eklenen SEMANTIK_TERCUME_REHBERI.md dosyasındaki anlam
öncelikli yönteme dayanır. Akademik yazım referansı yalnızca paragraf mimarisi,
akademik Türkçe ve kavram akışı içindir; oradaki kaynaklardan çevrilen metne
bilgi, iddia veya atıf aktarılmaz."""

QA_CHECKLIST = """### ÖZ DENETİM (hedef dosyayı yazmadan önce, sessizce yap)
- [ ] Kaynaktaki HER sayı dizisi (yıl, yüzde, ölçü, sayfa, tarih) hedefte aynen var mı?
- [ ] Kişi/kurum/kitap adları ve kısaltmalar doğru yazımla korunmuş mu?
- [ ] Glossary'deki her terim tutarlı karşılığıyla uygulanmış mı?
- [ ] Dipnot göndermeleri [fn N] biçiminde tam ve sıralı mı?
- [ ] Yasaklı kalıplar (oldukça, nitekim, zira, söz konusu, teşkil etmek vb.) yok mu?
- [ ] Hiçbir paragraf atlanmamış, hiçbir cümle özetlenmemiş mi?"""

PROMPT_TEMPLATE = """=== AI TRANSLATION PROMPT ===
Kaynak dosya: {rel_path}
Hedef dosya : {target_rel}
Çeviri stili: {style}
Kaynak dil  : {source_lang}
Hedef dil   : {target_lang}

=== BELGE İSKELETİ (okuma kolaylığı için) ===
{document_map}
=== /BELGE İSKELETİ ===

=== ANLAM ÖNCELİKLİ ÇEVİRİ PROTOKOLÜ ===
{semantic_protocol}
=== /ANLAM ÖNCELİKLİ ÇEVİRİ PROTOKOLÜ ===

=== KAYNAK METİN (aşağıdaki tüm içerik çevrilecek) ===
{source_text}
=== /KAYNAK METİN ===

=== ÇEVİRİ KURALLARI ===
{glossary_block}

- Sıfır özetleme: hiçbir paragraf, argüman veya dipnot atlanamaz.
- Dipnot referansları [fn 1], [fn 2] şeklinde metin içinde TAM korunmalı.
- Yukarıdaki glossary'deki terimler TUTARLI şekilde uygulanmalı.

### DOĞAL AKADEMİK TÜRKÇE (EN ÖNEMLİ KURAL)
Çeviri, Türkçede yazılmış özgün bir akademik makale gibi okunmalıdır.
Okuyucu, bunu bir çeviri olduğunu fark etmemelidir. Bunun için:

#### CÜMLE BOYU DENGESİ (KRİTİK)
- Cümle uzunluğunu mekanik bir hedef olarak kullanmayın; anlam birliği ve doğal
  Türkçe akışı belirleyici olsun.
- Bir cümlede birden fazla ana sav, özne veya mantıksal katman birbirine
  karışıyorsa, anlam ilişkisini koruyarak bölün.
- Kısa cümleleri yalnızca vurgu, geçiş veya kaynak yapısı gerektirdiğinde
  koruyun; uzun cümleleri de sırf kelime sayısı nedeniyle parçalamayın.
- Paragraf içinde cümle ritmini doğal biçimde çeşitlendirin. Sabit sayıda kısa,
  orta veya uzun cümle üretmeye çalışmayın.

#### VERİ KORUNUMU (SEMANTİK BÜTÜNLÜK)
- Kaynaktaki TÜM sayılar, yüzdeler, tarihler ve yıllar çeviride aynen korunmalıdır
  (ör. "1971", "%12,5", "3.500", "12/03/1954"). Rakamı yazıyla yazmayın, değerini
  değiştirmeyin.
- Özel isimler (kişi adları, ülke/kurum/kitap adları) doğru yazımla korunmalıdır;
  ilk geçişte açıklama gerekirse kısa bir karşılık eklenebilir ama ad asla
  atlanmamalıdır.
- Tarihler ve tarih aralıkları (ör. "1939-1945") kaynakta nasıl yazılmışsa o
  biçimle korunmalıdır.
- Çeviriyi bitirince bir kontrol geçişi yap: kaynaktaki her sayısal ve adsal
  birimin hedefte karşılığı var mı? Atlanan birim yoksa metin eksiktir.

#### ANLAM SADAKATİ
- Her paragraf, kaynaktaki argümanı eksiksiz taşımalıdır. Tek bir yan cümle
  bile atlanmamalıdır.
- Yazarın çekinceleri, vurguları ve derecelendirmeleri (kesinlik düzeyi) aynen
  korunmalıdır. "Belki", "muhtemelen", "kesinlikle" gibi ifadeler olduğu gibi
  aktarılmalıdır.
- Bağlam içinde geçen zamirlerin (this, that, these, those) göndergeleri
  Türkçede açık olmalıdır. "Bu durum", "bu nokta" gibi belirsiz ifadelerden
  kaçının; gerektiğinde "bu ayrım", "bu sorun" gibi somut gönderme yapın.
- Kaynakta ima yoluyla değil açıkça yazılmış olan her şey çeviriye aynı
  açıklıkta yansıtılmalıdır.

#### KAÇINILMASI GEREKEN İFADELER (yapay zeka çevirisi kokan kalıplar)
Şu ifadeleri KESİNLİKLE KULLANMAYIN:
- "teşkil etmek" -> "oluşturmak", "olmak", "niteliği taşımak"
- "bir dönüm noktası" -> "kırılma anı", "milat", "dönüşüm noktası"
- "mazhar olmak" -> "hedefi olmak", "konusu olmak"
- "önem arz etmek" -> "önemli olmak"
- "ifa etmek" -> "yerine getirmek"
- "belirtildiği üzere / daha önce de belirtildiği gibi" -> hiç kullanma
- "oldukça", "büyük ölçüde", "önemli ölçüde", "ayrıca", "nitekim", "zira",
  "diğer taraftan", "bununla birlikte", "bir başka ifadeyle", "şöyle ki",
  "söz konusu", "çok sayıda", "esas itibarıyla", "kanaatine göre" gibi
  yapay zeka çevirilerinde sık tekrar eden ifadeleri hiç kullanmayın.
- İngilizce terimlerin yanına parantez içinde orijinalini YAZMAYIN:
  ("top-down") gibi. Ya tamamen çevirin ya da İngilizcesini kullanın.

#### AKADEMİK MAKALE YAPISI (DERLİ TOPLU)
- Çeviri, özgün bir Türkçe akademik makale gibi akmalıdır. Her paragraf bir
  öncekinin üzerine inşa edilmeli, mantıksal geçişler doğal olmalıdır.
- Paragraflar birbirine "bağlaç zinciri" ile değil, anlam bağıyla bağlanmalıdır.
  "Ancak", "dolayısıyla", "böylece" gibi bağlaçları yalnızca gerçekten gerekli
  olduğunda kullanın; her paragraf başında bir bağlaç olması zorunlu değildir.
- Kaynakta dipnotla verilen bilgiler dipnot olarak korunmalı, metin içine
  gömülmemelidir. Dipnot numaraları [fn 1] formatında aynen kalmalıdır.
- Makalenin alt bölümleri (varsa) [SUBSECTION] etiketleriyle ayrılmalı;
  her alt bölümün kendi içinde giriş, gelişme, sonuç mantığı olmalıdır.

#### CÜMLE YAPISI VE AKIŞ
- CÜMLE ÇEŞİTLİLİĞİ: Her cümleyi aynı kalıpla başlatmayın. Özne-fiil-nesne
  sırasını tekrarlamayın. Kimi cümleye zarf, kimi cümleye nesne ile başlayın.
  Aynı bağlacı (ancak, fakat, çünkü, bu nedenle) üst üste kullanmayın.
- TÜRKÇE SÖZDİZİMİ: Kaynak dilin özne-fiil-nesne sırasını aynen taşımayın.
  Türkçede bilgi akışı önce eski/bilinen bilgi, sonra yeni bilgi şeklindedir.
  Cümleye gereksiz "bu, şu, o" ile başlamayın. Sıfatları üst üste yığmak
  yerine ilgi cümlecikleri kullanın.
- FİİL AĞIRLIKLI YAZI: İsim-fiil yapıları yerine çekimli fiiller kullanın.
  "X'in yapılması" yerine "X yapılır", "X'in bulunması" yerine "X bulunur".
- -DİR EKİNİ SADELESTİRİN: Tanım ve genelleme cümlelerinde ısrarla "-dır/-dir"
  kullanmayın. Türkçede "X Y'dir" yerine bağlama göre ek kullanmamak daha
  doğaldır.
- BAĞLAÇLARI AZALTIN: İngilizcedeki her "however, therefore, moreover,
  nevertheless"u Türkçede "ancak, bu nedenle, ayrıca, bununla birlikte" diye
  çevirmeyin. Çoğu zaman virgül veya "ise, da/de, -dığı için" yeterlidir.

#### TERİM VE ÜSLUP
- MODERN TÜRKÇE KULLANIN: Osmanlıca kökenli ağır kalıplar (teşkil etmek, mazhar
  olmak, arz etmek, zımınında, esas itibarıyla) yerine günlük akademik Türkçe
  karşılıklarını tercih edin.
- TEKRARDAN KAÇININ: Aynı kavram için hep aynı kelimeyi kullanmayın. "Önemli"
  yerine "kayda değer", "dikkate değer"; "çok sayıda" yerine "pek çok", "birçok",
  "sayısız" ile çeşitlendirin. Ancak terimlerde (ör. "imamet", "hilafet")
  tutarlı olun.
- ŞAHSİYET KULLANIMI: "şahsiyet" kelimesini en fazla 2-3 kez kullanın. Bunun
  yerine "kişilik", "kişi", "birey", "insan" tercih edin.
- DOĞAL AKADEMİK ÜSLUP: Yazarın yargısını güçlendirmeyin veya zayıflatmayın.
  Kaynakta ne kadar kesin/çekimliyse çeviride de o kadar olsun.
- NEOLOJİZM: Yerleşmemiş türetmeler (eylemlilik, insandışılaşma vb.)
  kullanmayın. Yerleşik akademik karşılığı olan terimleri yeğleyin.

### YAPISAL KURALLAR
- Çıktı SADECE çevrilmiş metin olmalı, açıklama/önsöz EKLEME.
- Yapı birebir korunmalı: [TITLE], [BODY], [SECTION], [FOOTNOTES] etiketleri
  ve p1:, p2: numaraları aynen kalmalı.
- Paragraf bütünlüğü: Her paragraf tek bir ana savı veya açıklama adımını görünür
  kılmalı. Aşırı uzun cümleleri, anlam ve dipnot bağlantısını koruyarak bölün;
  kopuk cümle parçaları ile "bu/şu/öyle" gibi belirsiz göndermeler bırakmayın.
- Terim kullanımı: Yerleşik Türkçe akademik karşılığı olan terimleri tercih edin.
  İlk geçtiği yerde zorunlu açıklama gerekiyorsa kısa bir karşılık verin; aynı
  kavram için metin boyunca farklı yazımlar, eğik çizgili çift karşılıklar ve
  gereksiz parantez içi eş anlamlılar kullanmayın.
- Hedef dosyayı yaz: {target_rel}
=== /ÇEVİRİ KURALLARI ===

{qa_checklist}
"""


def build_prompt(source_path: Path) -> str:
    """Kaynak dosya için AI asistanına verilecek çeviri promptunu üretir."""
    if not source_path.exists():
        raise FileNotFoundError(f"Kaynak yok: {source_path}")
    source_text = source_path.read_text(encoding="utf-8")
    if not is_structured_document(source_text):
        raise ValueError(
            f"Kaynak yapılandırılmamış ([BODY] etiketi yok): {source_path.name}"
        )

    config = load_config(source_path.parent)
    source_lang = infer_lang(source_path.name) or config.get("source_lang", "en")

    glossary = config.get("glossary", {}) or {}
    if glossary:
        glossary_lines = [f"  - {k} -> {v}" for k, v in glossary.items()]
        glossary_block = "Glossary (TUTARLI uygula):\n" + "\n".join(glossary_lines)
    else:
        glossary_block = "Glossary: (tanımlı değil)"

    prompt_override = (config.get("prompt_override") or "").strip()

    rel_path = source_path.relative_to(PROJECT_ROOT)
    target_rel = target_path_for_source(source_path).relative_to(PROJECT_ROOT)

    body = PROMPT_TEMPLATE.format(
        rel_path=rel_path,
        target_rel=target_rel,
        style=config.get("style", "academic"),
        source_lang=source_lang,
        target_lang=config.get("target_lang", "tr"),
        document_map=_build_document_map(source_text),
        semantic_protocol=SEMANTIC_PROTOCOL,
        source_text=source_text,
        glossary_block=glossary_block,
        qa_checklist=QA_CHECKLIST,
    )
    if prompt_override:
        body += f"\n=== BELGEYE ÖZEL EK KURAL ===\n{prompt_override}\n"
    return body


def _build_document_map(source_text: str) -> str:
    """Kaynak metnin tamamını tekrar etmeden yapısal okuma haritası üretir."""
    doc = parse_document(source_text)
    lines = [
        f"Başlık: {doc.title or '(başlık yok)'}",
        f"Bölüm sayısı: {len(doc.sections)}",
        f"Paragraf sayısı: {doc.paragraph_count}",
        f"Dipnot sayısı: {doc.footnote_count}",
    ]
    for section in doc.sections:
        numbers = [p.num for p in section.paragraphs if p.num]
        if numbers:
            first, last = numbers[0], numbers[-1]
            paragraph_range = f"p{first}" if first == last else f"p{first}-p{last}"
        else:
            paragraph_range = "numarasız paragraf"
        lines.append(
            f"- {section.section_id}: {section.title or '(başlıksız bölüm)'} "
            f"({paragraph_range}, {len(section.paragraphs)} paragraf)"
        )
    return "\n".join(lines)


def _auto_cleanup(tr_raw: str) -> str:
    """AI artıklarını temizler: kod çitleri, markdown ve fazla boş satır."""
    lines = [
        ln for ln in tr_raw.splitlines()
        if not re.match(r"^\s*```", ln)
    ]
    cleaned = "\n".join(lines)
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)
    return cleaned.strip() + "\n"


def apply_translation(source_path: Path, target_path: Path | None = None) -> dict:
    """Çeviriyi doğrular, otomatik temizlik uygular ve derler.

    Birincil çıktı Word (.docx); HTML yalnızca config `output_formats`
    içinde "html" geçiyorsa üretilir.

    Dönen yapı: {"ok": bool, "warnings": [...], "docx": yol | None,
                  "html": yol | None, "error": str?}
    """
    if not source_path.exists():
        return {"ok": False, "warnings": [], "error": f"Kaynak yok: {source_path}"}

    target = Path(target_path or target_path_for_source(source_path))
    if not target.exists():
        return {
            "ok": False,
            "warnings": [],
            "error": (
                f"Hedef yok: {target}. Önce yapay zeka asistanına "
                f"'{source_path.name}' dosyasını çevirttir, ardından "
                f"'{target.name}' dosyasını oluştur."
            ),
        }

    src_raw = source_path.read_text(encoding="utf-8")
    tr_raw = target.read_text(encoding="utf-8")
    if not is_structured_document(src_raw):
        return {"ok": False, "warnings": [], "error": f"Kaynak yapılandırılmamış: {source_path.name}"}
    if not is_structured_document(tr_raw):
        return {"ok": False, "warnings": [], "error": f"Hedef yapılandırılmamış: {target.name}"}

    cleaned = _auto_cleanup(tr_raw)
    if cleaned != tr_raw:
        target.write_text(cleaned, encoding="utf-8")

    warnings = validate_pair(source_path, target)
    config = load_config(target.parent)
    formats = [str(f).lower() for f in (config.get("output_formats") or ["docx"])]

    result: dict = {"ok": True, "warnings": warnings, "docx": None, "html": None}

    if "docx" in formats:
        try:
            from makale_pipeline.article_docx import export_article_docx

            info = export_article_docx(target, None, style=config.get("docx", {}))
            result["docx"] = str(Path(info["output"]).relative_to(PROJECT_ROOT))
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "warnings": warnings, "error": f"DOCX derlemesi başarısız: {exc}"}

    if "html" in formats:
        if not TEMPLATE_FILE.exists():
            result["warnings"] = warnings + [f"Şablon bulunamadı: {TEMPLATE_FILE}"]
        else:
            html = target.with_suffix(".html")
            if compile_document(target, TEMPLATE_FILE, html):
                issues = check_html_file(html, verbose=False)
                result["html_issues"] = issues
                result["html"] = str(html.relative_to(PROJECT_ROOT))
            else:
                return {"ok": False, "warnings": warnings, "error": "HTML derlemesi başarısız"}

    return result


def document_status(docs_dir: Path | None = None) -> dict:
    """Tüm belgelerin durumunu yapılandırılmış olarak döndürür.

    Dönen yapı: {"documents": [row], "pending_translations": n}
    """
    docs_dir = docs_dir or DOCUMENTS_DIR
    rows: list[dict] = []
    if not docs_dir.is_dir():
        return {"documents": [], "pending_translations": 0}

    for root, _, files in os.walk(docs_dir):
        p = Path(root)
        if p == docs_dir:
            continue
        sources = find_source_files(p)
        if not sources and "config.json" not in files:
            continue
        rel = p.relative_to(docs_dir)
        for src in sources:
            tr = target_path_for_source(src)
            docx = p / tr.name.replace(".txt", ".docx") if tr.name.endswith("_tr.txt") else None
            html = p / tr.name.replace(".txt", ".html") if tr.name.endswith("_tr.txt") else None
            structured = False
            if src.exists():
                structured = is_structured_document(src.read_text(encoding="utf-8"))
            rows.append({
                "path": str(rel),
                "source": src.name,
                "structured": structured,
                "translated": tr.exists(),
                "docx": docx.exists() if docx else False,
                "html": html.exists() if html else False,
            })
        if not sources and (p / "config.json").exists():
            for tr in p.glob("*_tr.txt"):
                if tr.name.endswith("_draft.txt"):
                    continue
                rows.append({
                    "path": str(rel),
                    "source": "(yok)",
                    "structured": False,
                    "translated": True,
                    "docx": (p / tr.name.replace(".txt", ".docx")).exists(),
                    "html": (p / tr.name.replace(".txt", ".html")).exists(),
                })

    rows.sort(key=lambda r: (r["path"], r["source"]))
    pending = sum(1 for r in rows if r["structured"] and not r["translated"])
    return {"documents": rows, "pending_translations": pending}
