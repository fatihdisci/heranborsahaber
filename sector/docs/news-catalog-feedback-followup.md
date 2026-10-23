# Şirket kataloğu, karar ayrımı ve geri alım kanıtı — 23 Ekim 2026

Yerel çalışma; mevcut değişiklikler korundu. Commit/push/deploy yok. Canlı veritabanına migration, INSERT, UPDATE veya DELETE uygulanmadı. Gerçek X/Telegram gönderimi yok. Model ve Hermes oturumları, KAP tercihleri değişmedi. Aktif filtre/hazırlık onayı oluşturulmadı.

## Geri alım ve Mini App

Yeni her raporun Kanıtlar verisinde kaynak URL/görsel hash/yayın tarihi/ham hücreler/sürüm yanında **işlem tarihi, tam kullanılan BIST30/BIST100 listeleri, resmî kaynak URL, alınma zamanı, snapshot SHA256, seçilmiş 10 hissenin sırası/nominal miktarı/grup gerekçesi** tutulur. Snapshot hash'i `sha256` alanı hariç JSON yükünü kapsar. Geçersiz/eski üyelikte snapshot null ve seçim gerekçesi membership_unknown olur. Eski raporlara geçmiş kanıt eklenmez.

Örnek yazı ve içerik DOM'undan bulunan görsel yeniden indirildi, gerçek Vision ızgara okuyucusundan geçirildi; 54 satırla yeni yerel önizleme üretildi. `reports/buyback-preview/evidence-preview.json` özellikle `local_preview_not_production_receipt` olarak işaretlidir. Endeksler 23 Ekim 14:48:49 İstanbul'da resmî KAP sayfasından alındı; test fixture üyeliği bu önizlemenin kanıtı değildir. Önizlemenin işlem tarihi 22 Ekim, yayın tarihi 23 Ekim'dir. Tweet 10 hisse; görsel tüm 54 satır. MASFN boş fiyat/tutarı ve nominal kaynak birimi korunur; kaynakta bulunmayan tutar hesaplanmaz.

Mini App'in Beğendiklerim/Beğenmediklerim sekmeleri ve sade Diğer menüsü korunur. Panel 7 gün/tür başına 750 kayıt ile bir çalışma görünümüdür; bütün oy geçmişini gösteren TXT bununla sınırlı değildir. Panel canlıya kurulmadı.

## Resmî şirket kataloğu

`src/data/news-companies.json`: KAP BIST Şirketleri sayfasının `data/content` listesinden tek anlamlı 4–5 karakterli kodu olan 710 şirket unvanı. Çok kodlu ihraççılar otomatik bir paya indirgenmez. Resmî sayfa URL'si, alınma zamanı, ham sayfa hash'i, katalog içerik hash'i ve hash içeren sürüm saklanır. Endeks üyeliği katalogda tutulmaz; KAP filtre davranışı değişmez.

Kısa adlar yalnız altı şirket için açıkça tanımlıdır: Aselsan, BİM, Ebebek, Akfen GYO, CarrefourSA ve Erdemir. Bunlar resmî yasal unvan/şirket profiline dayanır; diğer unvanlardan ilk kelimeyle otomatik takma ad üretilmez. Erdemir resmî KAP profilindeki web adresi/unvan ilişkisiyle bağlıdır. Carrefour ≠ CarrefourSA; tanımlı iştirak bağlamları (Erdemir Madencilik, Aselsan NET gibi) ana paya otomatik yazılmaz. Bu katalog bütün marka/iştirak ayrımlarını çözdüğü iddiasında değildir; belirsiz adlar çözümlenmemiş kalır. Kısa ad kapsamı ileride kaynakla gözden geçirilerek genişletilebilir.

Tekrar üretim: resmî `https://www.kap.org.tr/tr/bist-sirketler`, EREGL KAP profil sayfası ve `https://www.kap.org.tr/tr/Endeksler` HTML'lerini indirip dosyaların mtime'ını gerçek alınma zamanında koruyun; `node --import tsx scripts/build_news_catalog.ts companies.html eregli.html indices.html <çıktı-dizini>`. Çıktıyı incelemeden kaynak dosyasının üzerine veya canlı ayara kopyalamayın. Hazırlık kapısı gerçek kapsam/şirket/insan değerlendirmesi ister; katalog sağlanması bu onay değildir.

## Kök neden ve kural düzeltmeleri

- Boş şirket kataloğu isim eşleşmesini engelliyordu. Artık resmî katalog gölge değerlendirmede kullanılabilir.
- Yapay zekâ kelimesi finansal piyasa görüşünü teknoloji arşivine atıyordu. Piyasa bağlamı ve stratejist beklentisi ayrı tanınır.
- Bilanço kuralı yalnız bilanço/finansal tablo kelimelerine bakıyordu. Dönem net kâr/zarar sonuçları ve gerçekleşme fiilleri tanınır. “Beklentilerin üzerinde gerçekleşti”, gelecek beklentisine çevrilmez.
- Perakende indirim/aktüel katalog bağlamı şirketin finansal sonucu veya makro veri sayılmaz. Şirket adı tek başına anlık rota sağlamaz. Bu genel içerik türü kuralıdır; BİM kaynağı/şirketi yasaklanmaz.
- Ödeme aksaması/temerrüt, teklif, ihale kazanımı, imzalanmış sözleşme, ileriye dönük beklenti ve yalanlama farklı olay/aşamalardır. Fiil ekleri ve kelime sınırları dikkate alınır; başlık ezberi kullanılmaz.
- Kural sürümü `investor-v2`. Gerekli kaynak/tarih/yeterlilik kontrolleri ve hazırlık kapısı sürer; otomatik etkinleşme yok.

## Günlük geri bildirim raporu ve saklama

`/golgerapor` mevcut hazırlık/gölge özetinin yanında **endeks-geri-bildirim.txt** verir; kartlara düğme eklenmez. Başlangıç sorgusu sahibin tüm `news_interests` kayıtlarıdır; son 100 aday sınırı veya panel penceresi uygulanmaz. Kaldırılmış seçimler, eşleşmeyen/silinmiş haberler, mevcut karar ve tıklama geçmişi açıkça ayrılır. Tekrarlı callback makbuzu ikinci oy değildir; eski update yeni durumu geriye götürmez.

0005 eklemeli geçişi `news_interest_context` ile başlık/URL/kaynak gibi asgari metadata, `news_interest_snapshots` ile yeni kabul edilmiş tıklamanın **sonuç seçimi ve o andaki rota/gerekçe/kural/şirket kataloğu sürümünü** tutar. Mevcut oylar değiştirilmez. Eski kayıtlarda lookup metadata sağlanabilir ama geçmiş karar görüntüsü üretilmez. Kaynak bulunmazsa yok yazılır. Tam haber metni/özet kopyalanmaz. Bu asgari editör denetim kaydı mevcut geri bildirim defteriyle birlikte korunur; 7 günlük haber aday/tam kaynak saklama süresinden ayrıdır. Yeni davranışa canlı geçiş yapılana kadar canlı bot eski biçimde oy kaydetmeye devam eder; bu aralığın karar geçmişi sonradan doldurulmaz.

Salt okunur CLI: `node --import tsx scripts/export_interest_report.ts <news.sqlite> <yerel-secrets.json> <özel-çıktı-dizini>`. Yalnız sahibi okumak için yerel sır dosyasını kullanır, sırları/aktör kimliğini çıktıya yazmaz. SQLite readOnly + query_only + tek okuma transaction; migration çalıştırmaz. TXT dosyaları 0600 izinlidir ve repo dışında tutulur. Eski/yeni kararlar adayın kayıtlı değerlendirme zamanında karşılaştırılır; günümüz tarihiyle yeniden eskimiş sayılmaz. Özet silinmişse değerlendirme yapılmaz.

23 Ekim'deki son okumada 24 haber kaydı vardı: 4 beğeni, 19 beğenmeme ve 1 kaldırılmış seçim (25 düğme eylemi). Önceki 3/17'nin üzerine kullanıcı yeni oylar eklemiş; eski kayıtlar değiştirilmedi. 24 örneğin 6'sında alan/gerekçe farkı görüldü. Bu doğruluk veya başarı ölçümü değildir. Etiketlenmemiş sonuçlar için insan onayı yok. Beğeni instant, beğenmeme archive yerine geçirilmez; tıklanmama olumsuz değildir. Kalıcı kaynak/şirket/ülke/konu yasağı oluşturulmadı.

## Doğrulama

- Node 22.22.3 TypeScript kontrolü, 369/369 TS testi; Mini App, yetki/idempotency, yüksek hacim, hazırlık kapısı ve mevcut regresyonlar dahil.
- Mevcut PDF Python sanal ortamı: 64/64 test. macOS OCR 1 test ve geri alım ızgara OCR 3 test ayrıca çalıştırıldı; gerçek dış yayın yapılmadı.
- Worker dry-run build başarılı; gerçek deploy değil.
- Kit temiz üretim/yeniden açma: 89 dosyalı tam hash manifesti, transitif kaynaklar, runtime parity, 20 PNG örneği başarılı.
- Gerçek 54 satırlı PNG görsel olarak kontrol edildi. Önceki 3/150 görsel yerleşimleri ve 200 satır kapasite testi korunur. Tam tablo hiçbir yerde tweetin 10 satırına daraltılmaz.
- ZIP SHA256: `92984815eee2301e7cfbd3a273a21cfe786556972eda5648fd48bc4835574748`.

## Canlıya geçiş (yapılmadı)

İnceleme/onay sonrasında ilgili değişiklikler commit/push, başarılı CI, tutarlı yerel SQLite yedeği, staged kurulum ve yalnız Endeks Haber geçişi gerekir. 0004/0005 geçişlerini önce yedek kopyada doğrulayın; işlem öncesi/sonrası oy sayısı ve integrity kontrol edin. Panelin snapshot/sync sürümü ve mevcut bulut bağlantısı ayrıca doğrulanmalı. Canlı panel senkronizasyonunun önceki incelemede hata verdiği görülmüştü; bu çalışma bunu canlıda gidermiş sayılmaz.

Filtre shadow ve otomatik seçki kapalı kalmalı. İlk gerçek rapor Kanıtlar/PNG üzerinden editörce incelenmeli; yalnız açık Paylaş eylemi yayın yapar. Başarısızlıkta önceki uygulama sürümüne dönün; yeni denetim tablolarını silmeyin, gönderim kuyruğunu yeniden oynatmayın. Uygulama geri dönüşü ile veritabanı kurtarması farklıdır; veri kurtarma için tutarlı yedek ayrıca değerlendirilmelidir.

Canlı geçiş incelemesi: yeni geri alım tarayıcısı ilk çalışmada `buyback_discovery_since` sınırını atomik kaydeder. Önceden işlenmemiş eski raporlar gönderilmez; kayıtlı raporun düzeltmesi ve sınırdan sonraki yeni yayınlar mevcut korumalarla işlenir. Başlangıç/yeniden başlatma regresyonu eklendi.
