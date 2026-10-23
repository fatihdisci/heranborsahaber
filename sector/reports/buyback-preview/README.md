# Mini app ve İş Yatırım geri alım raporu — 23 Ekim 2026

Yerel uygulama/test teslimidir. Başlangıç: main, `1f5deb01014897ac6c5c4e75dcdbf901f1ff4dc5`. Commit, push, deploy ve canlı ayar değişikliği yapılmadı. Gerçek X/Telegram test gönderimi yok.

## Mini app

Akış, Hazır içerikler, Beğendiklerim ve Beğenmediklerim sekmeleri; açık işlem adları; ikincil kaynak/kaydet işlemleri açılır Diğer alanında. Yayın özeti ve filtreler katlanabilir. Kopyalama düğmesi kaldırıldı. Sahibe ait mevcut beğeni kayıtları salt okunur aktarılır; rota kararına çevrilmez. Panelin mevcut 7 gün / tür başına 750 kayıt sınırı korunur; tam geçmiş arşivi değildir. Telegram bağlantısı bot sohbetini açar, tek başına yayın/düzenleme başlatmaz. Gerçek işlemler Telegram kartında devam eder.

Yerel sahte veriyle beğenilen/beğenilmeyen filtreleri, detay ve Diğer menüsü tarayıcıda kontrol edildi (`miniapp-diger.png`). Canlı panel güncellenmedi.

## Yeni rapor

- RSS: https://arastirma.isyatirim.com.tr/category/gunluk-raporlar/pay-geri-alimlari/feed/
- İncelenen yazı: https://arastirma.isyatirim.com.tr/2026/10/23/pay-geri-alimlari-23-10-2026/
- Yayın: 23.10.2026 09:08:50 Türkiye; işlem tarihi: 22.10.2026.
- Tam görsel bağlantısı yazının içerik DOM'undan bulunur. Dosya/gün URL'si tahmin edilmez; birden çok belirsiz aday varsa inceleme gerekir.
- Mevcut macOS Vision okuyucusu + fiziksel tablo ızgarasıyla 54 satır, her satırda 5 kaynak hücresi. Kaynakta boş hücre null, PNG'de —, CSV'de boş. MASFN fiyat/toplamı boş korunur. ADGYO toplamı kaynakta 2.799.860; yuvarlanmış fiyat × miktar ile değiştirilmez.
- Nominal pay tutarı lot/adet diye adlandırılmaz. Kaynak değerleri için KAP veya ikinci kaynak sorgusu yok; bağımsız doğrulanmış veri iddiası yok. Son kontrol editöre ait.
- Tweet: BIST30 → BIST100 dışı olmayan kalan üyeler → diğerleri; her grupta nominal miktar azalan, eşitlikte kod. En çok 10 farklı kod. Üyelik yalnız güncel/tam kayıt geçerliyse kullanılır; bilinmiyorsa nominal sıralama uygulanır ve editör notunda bildirilir.
- Yeni yerel önizlemede üyelik kaydı: https://www.kap.org.tr/tr/Endeksler, 23.10.2026 14:48:49 Türkiye. Liste doğrudan resmî sayfadan alındı; `evidence-preview.json` tam üyelik listesi ve hash ile bağlanır. Bu üretim makbuzu değil, yeni yerel önizlemedir. Önceki fixture üretim kanıtı olarak kullanılmaz; canlıda mevcut yerel endeks önbelleği salt okunur kullanılır, 36 saati geçen kayıt geçerli sayılmaz.
- Tweet 101 X ağırlıklı karakter; twitter-text 3.1.0 ile ölçülür. Tweet/görselde kaynak veya saat yok. URL, özgün görsel anahtarı/hash'i, ham değerler, sürüm ve eksiklikler Kanıtlar görünümündedir.
- PNG: beyaz/lacivert, sabit büyük başlık, işlem tarihi. 1–3 sütun bloğu, 28–32 px veri yazısı, ölçülmüş metin genişlikleri; en çok 200 satır, 4096 px kenar ve 16 MP sınırı. Uzun değer veya kapasite aşımı sessiz kesilmez; inceleme durumuna alınır. PNG ayrıca 5 MB ile sınırlanır.
- Kaynak şablonu değişir, satır/hücre okunamaz veya tarih/sayı bozuksa otomatik içerik hazır kabul edilmez. `/durum` inceleme gerekçesini gösterir. Bu ilk sürüm kaynakta gördüğümüz ızgaralı formatı destekler; değişen format için okuyucu güncellemesi gerekebilir.

## Akış ve tekrar koruması

Yerel servis güncellendiğinde 10 dakikada bir RSS'nin son 48 saatteki en yeni raporunu kontrol eder. Yeni rapor yoksa eski veri bugünün tarihiyle üretilmez. URL + görsel SHA ve anlamlı tablo sürümü kayıtlıdır. Aynı tablo farklı görsel baytlarıyla gelirse ikinci içerik oluşmaz. Değişen tablo Düzeltme olarak hazırlanır. Önceki teslimat/gönderim belirsiz veya sürüyorsa yeni sürüm incelemeye alınır; kör yeniden gönderim yapılmaz. Süresi dolmuş okuma lease'i yeniden alınabilir.

Yeni kaynak ve eski KAP günlük üreticisi işlem günü başına tek kayıt alanını paylaşır. Eski rapor varsa yeni kaynak ikinci ürün oluşturmaz; yeni kaynak varsa aynı gün eski üretici durur. Yeni rapor, mevcut drafts → Telegram inceleme → açık X paylaşımı akışını kullanır. Otomatik X yayını yok.

0004 geçişi yalnız yeni rapor makbuz/gün tablolarını ekler. Canlı veritabanına uygulanmadı. Devreye alma ayrıca staged kurulum, tutarlı yerel yedek, CI ve geri dönüş doğrulaması gerektirir. Uygulama geri dönüşünde yeni tabloları silmek veya eski gönderimleri yeniden oynatmak gerekmez.

## Doğrulama

- Node 22.22.3: TypeScript kontrolü başarılı; 369/369 test başarılı.
- Dry-run Worker build başarılı; deploy yapılmadı.
- Mevcut PDF sanal ortamında 64/64 Python testi başarılı. Buna geçici dizine yeni derlenen Swift/macOS Vision testleri ve gerçek 54 satırlı OCR karşılaştırması dahil.
- 3, 54, 150 satırlı gerçek PNG'ler görsel olarak incelendi. 200 satır otomatik render/sınır testinde geçti; 201 satır açık kapasite hatası verir. 3 ve 150 örnekleri sentetiktir; gerçek şirket verisi gibi paylaşılmaz.
- İzole veri tabanı/sahte ağ ile ilk üretim, tekrar, düzeltme, beklenmeyen hücre, eski veri, KAP çakışması, yarım kalan okuma ve belirsiz teslimat koruması test edildi.
- ZIP temiz üretildi; yeniden açılıp bütün manifest hash'leri, eksik import, runtime-kaynak eşitliği ve 20 PNG doğrulandı. Önceki 19 örnek korunur.
- ZIP SHA256: `92984815eee2301e7cfbd3a273a21cfe786556972eda5648fd48bc4835574748`.

Başlıca değişen dosyalar: `src/is-buyback.ts`, `src/buyback-pipeline.ts`, `src/buyback-card.ts`, `src/buyback-types.ts`, `src/report-text-metrics.ts`, `scripts/read_buyback_image.py`, `scripts/buyback_reader.ts`, `scripts/local_service.ts`, `src/kap-report-save.ts`, `src/editor-tools.ts`, `src/draft-assets.ts`, `src/editorial.ts`, `src/output-preferences.ts`, `src/report-card.ts`, `src/telegram-ui.ts`, `src/types.ts`; panel snapshot/sync ve miniapp public dosyaları; 0004/baseline migration; kaynak fixture/testler; package/lock; CI macOS kontrolü; ChatGPT kit prompt/export/ZIP.

## Ek düzeltme: tweet hisse kodları

Devre kesici tweetlerinde toplu kod öznesi başlık/gövdeden çıkarılır; kodlar en üst hashtag satırında tek kez kalır. Negatif durum ifadeleri korunur. Birbirinden farklı hisse durumları gruba genellenmez; anlam kaybı riski varsa açık düzenleme hatası verilir. Diğer tweet türlerinde bilinen kodlar son metin katmanında #KOD olarak biçimlenir; URL ve kaynak/kanıt metinleri değiştirilmez. İlgili dosyalar: src/tweet-tickers.ts, src/editorial.ts, test/tweet-tickers.test.ts, kit prompt/ZIP. Tek/çok kod, apostrof, .E, tekrar, olumsuz durum, farklı durumlar ve farklı şablonlar için üç yeni regresyon testi geçti. Python kodu bu ek düzeltmede değişmedi. Commit/push/deploy yapılmadı.
