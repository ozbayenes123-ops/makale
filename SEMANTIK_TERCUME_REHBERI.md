# Anlam Öncelikli Çeviri Rehberi (özet)

Bu dosya `translator.py` içindeki `SEMANTIC_PROTOCOL` ve çeviri promptunun
dayanağıdır. Kural: önce anlam örgüsünü kavra, sonra Türkçe akademik metin
olarak yeniden kur.

## 1. Ön okuma (çevirmeden önce)
- Belgenin tamamını ve ilgili bölümü oku: başlık, bölüm sırası, temel
  kavramlar, ana iddia, paragraf ilişkileri.
- Her paragraf için zihninde sabitle: ana sav → kanıt/örnek → niteleme →
  sonraki paragrafa geçiş.

## 2. Paragraf disiplini
- Her `p<num>` bloğu tek anlam birimidir; işlevi ve sırası korunur.
- Cümle bölünebilir/birleştirilebilir; iddia-kanıt ilişkisi ve dipnot bağı
  bozulamaz. Kaynakta olmayan paragraf, yorum, sonuç, vurgu eklenemez.

## 3. İlişki ve gönderim
- Karşıtlık/neden/sonuç/örnekleme/sınırlama/geçiş ilişkisi doğru kurulur;
  kaynakta olmayan ilişki kurulmaz.
- Zamir göndergeleri Türkçede açıklaştırılır ("bu ayrım", "bu sorun").

## 4. Kesinlik derecesi
- Kip/ihtiyat/yükümlülük/istisna ifadeleri (may, might, likely, argues,
  suggests, must, shall, except) daha kesin veya daha zayıf hükme
  dönüştürülmez.

## 5. Veri bütünlüğü
- Sayı, yüzde, tarih, yıl, ölçü, özel isim, olumsuzluk, koşul, alıntı,
  dipnot: tamamı korunur, hiçbiri özetlenmez.

## 6. Çift sessiz kontrol (taslaktan sonra)
1. Bağlam okuması: paragraf geçişleri, kavram tutarlılığı, zamir gönderimi.
2. Sadakat okuması: kaynak-hedef veri, iddia, kip, dipnot eşleşmesi.
