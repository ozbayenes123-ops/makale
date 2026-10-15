# Turkish Naturalness Review (EN→TR akademik metin, ikinci geçiş)

Amaç: çevirisi bitmiş Türkçeyi kaynağın cümle iskeletinden kurtarmak. Kural
değil, teşhis kalıplarıdır; bağlam her zaman üstün gelir. Bu belge geneldir:
hiçbir kullanıcıya, projeye veya makaleye atıf içermez.

## Çekirdek test

> Bu anlam bana kaynağın kelimeleri olmadan ulaşsaydı, Türkçe cümleyi
> kurarken yine bu yapıyı mı kullanırdım?

Cevap hayırsa cümleyi anlamından yeniden kur. Kelime yamalamakla yetinme.

## Hata sınıfları (gerçek kusur türlerinden derlenmiştir)

1. **Yerinden oynamış öğeler.** İngilizce sıralama korununca nesne/yan cümle
   fiilden sonra kalır: `... parçalanmasına borçludur ayrı birer siyasal
   varlık olarak varoluşlarını.` → öğeyi fiilden önceye al.
2. **Gereksiz zamir.** Bağlam açıkken `kendisi, kendisinin, kendi, onların`
   düşürülür; yalnızca gerçek vurgu (`bizzat`, "itself" anlamı) kalır:
   `Weber'in kendisinin ısrar ettiği gibi` → `Weber'in ısrar ettiği gibi`;
   `kendisini izleyen anayasalar` → `sonraki anayasalar`.
3. **Sözcükte kalma (kalıp tercüme).** `bedelini taşımak` → `bedeli olmak`;
   `bir eki olmak` → `tamamlayıcısı olmak`; `el konularak toplanan artık` →
   `artığın toplanması`; `prescription`'ın birebir `reçete`'si yerine `çare`;
   `cripple`'ın `topal bırakmak`'ı yerine `baltamak`; `beneficiary`'nin
   `kâr sağlayan`'ı yerine `kazanım sağlayan`; `possession`'ın `zilyedlik`'i
   yerine `özel mülkiyet`; `ordinarily`'nin `sıradan olarak`'ı yerine
   `genellikle`.
4. **Kayan özne/kalıntı cümle.** `... başlamasını farklı bir itki sağladı`
   gibi İngilizce iskeletten kalan öznesiz-tanımsız cümleleri Türkçe çekirdek
   cümleye oturt: `başlangıcı farklı bir itkiyle harekete geçti`.
   Niteleyici yığınlarını böl: `Sivil idareler daha kapsamlı, farklılaşmış ve
   yetkin hâle geldi` → `kapsamı genişledi, işlevleri ayrıştı, yetkinlikleri arttı`.
5. **Ek/hâl hataları.** `ihtiyaçlarınca` → `ihtiyaçlarıyla`; çoğul ekinden
   sonra kesme yok: `Paşalar'ın` → `Paşaların`; `himayeleri altında` →
   `himayesi altında`.
6. **Türkçe katmanındaki yazım kusurları.** Harf tekrarı (`katılımsı`),
   künyeden sonra artakalman tırnak (`2019)." Bütün`), yanlış kelime
   (`tedirler` → `tedbirler`, `gömen` → `geçersiz kılan`).
7. **Künye hijyeni.** `s. p.17` → `s. 17`; isim yazım hataları düzeltilebilir
   (`Mazourki` → `Marzouki`, `Eslamf` → `Eslami`, `Encyclepedia` →
   `Encyclopaedia`). Ama KAYNAĞIN KENDİ yazım/fihrist hataları (`product
   cotton crisis`, `s. ivx`) bilerek korunur: önce iki bağımsız metin çıkarma
   motoruyla ya da vision ile basılı metni doğrula; hataysa `[sic]` notunu
   yalnızca kullanıcı isterse ekle. Kaynağı düzeltmek çeviri değildir.
8. **Zaman/bağlaç kayması.** `gelir ... yapardı` → `gelirdi ... yapardı`;
   özetleme bağlaçları: parafraz olmayan yerde `Başka bir deyişle` değil
   `Böylece`.
9. **Eşdizim bulanıklığı.** `ve/ya da` neyi bağladığı belirsizse cümleyi böl
   (`reformların ve X'in kaldırılmasını talep eden gösteriler` gibi
   ikilikleri açık bağlama kavuştur).
10. **Bozuk kaynak metin serbesti değildir.** Kaynak kendisi anlamsızsa bile
    okunabilir ama sadık bir Türkçeyi seç (`prescription` → `çare` gibi) ve
    raporda not düş; anlam uydurma, kanıt ekleme.

## İşleyiş

1. `_tr.txt` dosyasını baştan sona oku; yukarıdaki sınıflar için cümleleri
   tara. Yararlı tarama kalıpları: `kendisi`, `kendi `, `s. p.`, `.,`,
   `katılımsı`, `tedirler`, `Bunton.` vb.
2. Semantik şüphe varsa önce EN çiftinde aynı cümleyi bul (`search_files`)
   ve anlam eşitliğini doğrula; sonra yeniden yaz.
3. Yamaları hedefli uygula (`patch`); ardından eski ifadelerin kalmadığını
   `search_files` ile kanıtla (bkz. Pitfalls).
4. `validate_document` + `quality_scan` koşusu; derlemeyi `translate_apply`
   ya da `export_docx`/`export_pdf` ile yenile ve paragraf sayılarının
   değişmediğini doğrula (55→55, 73→73 gibi).
5. Raporu sınıfa göre sayılarla ver; bilerek korunan kaynak hatalarını ayrı
   maddede açıkla.

## Pitfalls

- `patch` yamaları tırnak karakterlerine duyarlıdır: dosyada düz `'` varken
  `'` ile yazılan yama sessizce başarısız olabilir. Her toplu yamadan sonra
  eski ifadelerin gerçekten kalktığını grep ile doğrula.
- Tek olmayan `old_string` (aynı künye 4 yerde geçiyorsa) hata döner;
  `replace_all` kullan ya da bağlamı genişlet.
- Vision kapasite dolu/yavaşsa aynı görselle döngüye girme: dijital PDF'lerde
  iki bağımsız metin çıkarma motorunun aynı sonucu vermesi yeterli kanıttır;
  görsel doğrulamayı ertelenmiş iş olarak raporla.
- Doğal Türkçeyi "daha resmî" diye bozma; kısa ve akıcı cümle korunur.
  Aşırı düzenleme (`tek bir onarım kalıbının tüm cümlelere kopyalanması`)
  ayrı bir kusurdur.