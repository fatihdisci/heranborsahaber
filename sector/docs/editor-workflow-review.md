# Endeks Haber editör iş akışı — inceleme teslimi

23 Ekim 2026. Başlangıç ve güncel uzak main: `e42c884`. Çalışma dalı: `work/editor-workflow`. Kullanıcı çalışma ağacı başlangıçta temizdi; remote yeniden kontrol edildi, daha yeni main commit'i yoktu. Değişiklikler yerel çalışma ağacında bırakıldı. Commit/push/deploy yapılmadı. Canlı servis durdurulmadı; ikinci tüketici veya gerçek X/Telegram/model test çağrısı çalıştırılmadı. Canlı veritabanı değiştirilmedi.

Bu ilk teslimin takip düzeltmeleri ve güncel test/ZIP sonuçları için [takip incelemesi](editor-workflow-followup.md) geçerlidir. Aşağıdaki ilk teslim sayıları tarihsel kayıttır.

## Uygulananlar

| Alan | Dosyalar / davranış |
|---|---|
| Haber rotaları | `src/news-routing.ts`, `newsroom.ts`, `pipeline.ts`, `news-inbox.ts`: açıklanabilir anlık/seçki/arşiv; metadata puandan önce saklanır. Varsayılan gölge mod, ayrı sahip onayı olmadan aktif mod yok. |
| Tekrar ve olay | Aynı/yeni URL'deki değişen tutar, dönem, karar/beklenti/iptal/yalanlama korunur. Tam kopyalar olay grubunda toplanır; belirsiz ilişkiler öneridir. `/olay` sahibin açık ilişkisini kaydeder; ilişkiler otomatik bastırma değildir. Ajans ailesi bağımsız teyit sayılmaz. |
| Geri bildirim | Önizlemede neden / ilgisiz / tekrar / acil değil; `/aday` ve `/golgerapor`. Tıklanmama öğrenme sinyali değildir. Tek geri bildirim şirket veya kaynak susturmaz. |
| Seçki | Ayrı açık onay ve enable bayrağı, ayarlanabilir 12:30/18:30 İstanbul saatleri; 15 dakikalık kısa kesinti telafisi, kalıcı teslimat kaydı ve sabit aday listesi. Açık 429 reddi sınırlı tekrar; belirsiz teslimat yeniden gönderilmez. Boş otomatik seçki mesaj üretmez. |
| Ortak çıktı | `output-preferences.ts`, `editorial.ts`, `card.ts`, `report-card.ts`: açık tüm-liste/ilk N ve alış/satış seçimi ortak satırlara uygulanır. Seçilmemiş satış kodları alış tweetine sızmaz. Kapasitede hata; satır atma/thread açma yok. Canlı ön denetim ve kit aynı tercih katmanını kullanır. |
| Editör araçları | `editor-tools.ts`, `card-redesign.ts`, `telegram.ts`, `draft-assets.ts`, `worker.ts`: orijinal PNG; veri/kanıt inceleme; hedefli label/value düzeltmesi ve önce/sonra kaydı; mevcut model/kanıt denetimiyle yeniden üretim. Düzen menüsü yalnız desteklenen şablonlarda. |
| Yayın geçmişi | `publication-snapshot.ts`, `publication-assistant.ts`, `publication-report.ts`, `x-publish.ts`: yayın/beyan revision'ı, metin ve gerçek PNG SHA256; API makbuzu ile snapshot atomik kaydedilir. Manuel URL ayrı kullanıcı beyanıdır. Eski kayda bugünkü taslak uydurulmaz. |
| Gözlem / sağlık | Nitter yeniden kurulmadı. Çift sayıda aralığın medyanı düzeltildi; rapor 23.00 kesiminde, geç gönderilen rapora 23.00 sonrası tweet katılmaz. `/durum` sahip erişimlidir. Panelin salt okunur sınırı değiştirilmedi. |
| Şema / CI | `0002_editorial.sql` yalnız ek tablo/index oluşturur; yerel başlangıç şeması da eşlenmiştir. İki CI tek `checks.yml` dosyasına toplandı: Node 22/TypeScript/kit/dry-run, Python 3.13 ve 3.12, ayrı macOS Vision OCR. |

KAP toplayıcısının kapsam, endeks ve teslimat kuralları değiştirilmedi; `kap/rules.ts`, `ticker-scope.ts`, `collector.ts`, `kap-delivery.ts`, `index-tags.ts` değişmedi. KAP tarafındaki değişiklik yalnız istenen rapor çıktısı/kapsam tercihi ve sessiz 30-satır kesmesinin kaldırılmasıdır. Geri alımın varsayılan ilk-10 ürünü korunmuştur. Model `gpt-6-luna/medium`, Hermes oturum düzeni ve açık Paylaş onayı korunmuştur.

## Kontroller

- Yeni regresyonlarda saat sabitlenmiştir; dış model/X/Telegram taşıyıcıları sahtedir.
- Node 22: `npm run check` başarılı.
- TypeScript: **323/323 test başarılı** (başlangıçtaki 300 testin davranışları korunarak yeni regresyonlar eklendi; yoğun rapor testi artık açık kapasite hatasını bekler).
- `npm run build`: Wrangler dry-run başarılı; deploy yapılmadı.
- Python: 61 test, 60 başarılı / 1 macOS OCR varsayılan olarak atlandı.
- macOS OCR ayrı: Swift kodu geçici dosyaya derlendi, `test_macos_ocr.py` 1/1 başarılı.
- `git diff --check`: başarılı.
- Uzak Actions çalışması ve gerçek model/X/Telegram teslimatı yapılmadı.

Kit ZIP yeniden açılarak manifestin tam dosya kümesi ve hash'leri, transitif yerel kaynak bağımlılıkları, yeniden derlenmiş runtime eşleşmesi ve 19 gerçek PNG doğrulanır. Kurum ve AKD örnekleri ayrıca görsel olarak incelendi; yeni tüm-liste regresyonu gerçek PNG üretir. Sınır/sınır+1 kapasite testleri satır kaybı yerine hatayı doğrular.

Kritik regresyonlar: karar/beklenti, iddia/yalanlama, şirket adı olmayan önemli makro olay, endeks dışı önemli şirket, farklı finansal dönem/tutar, aynı kaynak kopyası, aynı URL güncellemesi, tarihi bilinmeyen adayın tarih uydurmadan manuel okuyucuya gitmesi ve tekrarlanan tıklamanın işi çoğaltmaması, seçilmemiş kod sızıntısı, tüm satırlar/yoğun tablo, sahip kontrolü, yeniden başlatma/429/belirsiz teslimat, değişen taslaktan bağımsız yayın geçmişi, dolu eski SQLite şemasında leased iş ve uncertain yayın korunumu, ağ kapalı geçici dosya yedeğinden geri yükleme ve integrity_check.

ZIP: `exports/ENDEKS-HABER-ChatGPT.zip`

SHA256: `61e152cd1039087d217c83c4158e4a52d9ffe1a5d20227d059495ed4c959c755`

## Gölge değerlendirmesi ve onaylı geçiş

Şu anda hiçbir canlı karar değiştirilmedi. Gölge modda eski filtre altında kalan adaylar da kayıtlıdır (`legacy_eligible=0`). Temsilî bir örneklemde editör `/aday` ile rota etiketi verir. `/golgerapor` kritik kaçırma, önemli haberi arşivleme, yanlış kritik ve önizleme gecikmesini bu insan etiketleriyle karşılaştırır. Tekrar geri bildirimleri de izlenir. Henüz gerçek trafik üzerinde ölçülmüş bir iyileşme oranı veya hatasızlık iddiası yoktur; bildirim azalması tek kabul ölçütü değildir.

Etkinleştirme için ayrıca push/deploy ve canlı veri yedeği onayı gerekir. Sonrasında önce **gölge modda** doğrulama yapılır. Aktif filtre için ayrı sahip onayının yanında artık sürümlü şirket/kapsam/insan etiketli değerlendirme hazırlığı zorunludur; yalnız `mode=active` ve `approved_by_owner=true` yeterli değildir. Güncel [hazırlık sözleşmesine](news-filter-readiness.md) bakın. Otomatik seçki ayrıca `digest_enabled=true` gerektirir; saatler `digest_times` içindedir. `activated_at` gerçek onay zamanına ayarlanmalı, `news_preview_since` aynı zamanın ISO değerine ilerletilmelidir. Eski arşiv yeniden bildirim kuyruğuna dökülmemelidir. Bu rapordaki ayarlar şu an uygulanmadı.

Filtre geri dönüşü: `mode=shadow`, `approved_by_owner=false`, `digest_enabled=false`; önizleme başlangıcı geri dönüş anına ilerletilir. Kaynak, arşiv, kuyruk ve teslimat makbuzları silinmez. Gönderim sonucu belirsiz kayıtlar elle incelenir, replay yapılmaz.

Uygulama rollback'i önceki kod sürümüne dönüş işlemidir; ek tabloları silmeyi gerektirmez. Veri kurtarma ise tutarlı SQLite yedeği, WAL/checkpoint durumu ve medya bütünlüğüyle ayrı ele alınmalıdır. Gerçek üretim yedeğinin konumu ve şifreleme anahtarı bu çalışmada belirlenmedi; dış depoya veri yüklenmedi. Geri yükleme testi yalnız geçici ve sentetik veri üzerinde yapıldı.

## İnceleme öncesi açık sınırlar / kararlar

- Doğrulanmış şirket/kurum eşleştirme sözlüğü ve takip listesi `news_filter_preferences.entities/watchlist` ile yapılandırılır. Varsayılan sözlük boştur; doğrulanamayan şirket ilgisi arşive atılmak yerine seçkiye gider. Endeks önceliği için kullanılacak sözlük gerçek resmî eşleşmelerle gözden geçirilmeden aktif moda geçilmemelidir; ad benzerliğiyle kod tahmini yapılmaz.
- Genel geri alım raporu tüm-liste ürünüdür. İlk-N altkümesi için toplamları yeniden hesaplama bu sürümde desteklenmez ve hata verir. Normal ilk-10 geri alım komutu sürer. Çoklu kart/thread kararı kullanıcıya bırakıldı.
- İlk hedefli hücre editörü buy/sell/holdings/metrics altında label/value alanlarını düzenler. Birim değer metninde, yön panelde, ölçüm dönemi mevcutsa ayrı görünür; bilinmeyen dönem tahmin edilmez. Ayrı dönem/yön editörleri yerine mevcut genel Düzenle akışı kullanılabilir.
- İlk sürüm olay ilişkilerini önerir ve sahibin açık ilişkisini kaydeder. Otomatik yaşam döngüsü birleştirmesi veya belirsiz ilişkiyle haber bastırma yoktur.
- Genel metin haberlerinde eski varsayılan tweet seçimleri korunur; açık `output_preferences` bunlara önceliklidir. Kaynakta yapılandırılmış satırlar varsa deterministik kapsam doğrulaması yapılır; ham görüntüden çıkarımın doğruluğu mevcut vision/kanıt denetimine bağlıdır.
- GitHub salt okunur kontrolde main branch protection için “Branch not protected”, dal ruleset kontrolünde boş liste döndü. Uzak Actions bu değişikliklerle çalıştırılmadı (push yok). Sonradan koruma eklenirse `application`, `macOS Vision OCR (isolated)`, `Python 3.12 compatibility` iş adlarıyla gereksinimler eşlenmelidir.

## Dosya indeksi

- `.github/workflows/checks.yml` (değişti)
- `.github/workflows/ci.yml` (kaldırıldı)
- `sector/README.md` (değişti)
- `sector/docs/chatgpt-kit-prompt.txt` (değişti)
- `sector/docs/chatgpt-kit-readme.txt` (değişti)
- `sector/exports/ENDEKS-HABER-ChatGPT.zip` (değişti)
- `sector/migrations/0001_sector.sql` (değişti)
- `sector/scripts/kap_reports.ts` (değişti)
- `sector/scripts/local_service.ts` (değişti)
- `sector/scripts/manual_reader.ts` (değişti)
- `sector/scripts/validate_draft.ts` (değişti)
- `sector/src/ai.ts` (değişti)
- `sector/src/bridge.ts` (değişti)
- `sector/src/card-redesign.ts` (değişti)
- `sector/src/card.ts` (değişti)
- `sector/src/dedupe.ts` (değişti)
- `sector/src/draft-assets.ts` (değişti)
- `sector/src/editorial.ts` (değişti)
- `sector/src/ingest.ts` (değişti)
- `sector/src/kap/reports.ts` (değişti)
- `sector/src/manual.ts` (değişti)
- `sector/src/news-inbox.ts` (değişti)
- `sector/src/nitter-account.ts` (değişti)
- `sector/src/nitter-daily-report.ts` (değişti)
- `sector/src/pipeline.ts` (değişti)
- `sector/src/publication-assistant.ts` (değişti)
- `sector/src/publication-report.ts` (değişti)
- `sector/src/report-card.ts` (değişti)
- `sector/src/style.ts` (değişti)
- `sector/src/telegram-commands.ts` (değişti)
- `sector/src/telegram.ts` (değişti)
- `sector/src/types.ts` (değişti)
- `sector/src/worker.ts` (değişti)
- `sector/src/x-publish.ts` (değişti)
- `sector/test/kap-reports.test.ts` (değişti)
- `sector/test/telegram-commands.test.ts` (değişti)
- `sector/docs/editor-workflow-review.md` (yeni)
- `sector/migrations/0002_editorial.sql` (yeni)
- `sector/src/editor-tools.ts` (yeni)
- `sector/src/news-routing.ts` (yeni)
- `sector/src/newsroom.ts` (yeni)
- `sector/src/output-preferences.ts` (yeni)
- `sector/src/publication-snapshot.ts` (yeni)
- `sector/test/editor-workflow.test.ts` (yeni)
- `sector/test/news-routing.test.ts` (yeni)
