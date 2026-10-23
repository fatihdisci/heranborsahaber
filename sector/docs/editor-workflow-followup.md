# Editör iş akışı — takip düzeltmeleri

23 Ekim 2026. Dal: `work/editor-workflow`. Başlangıçtaki commit edilmemiş değişiklikler korundu. Bu teslim kod, test, belge ve üretilen kit ZIP'i ile sınırlıdır. Commit/push/deploy yapılmadı; canlı ayarlar, veritabanı, servisler, filtre ve seçki değiştirilmedi. Gerçek model/X/Telegram çağrısı veya ikinci bot tüketicisi çalıştırılmadı.

## Düzeltilen davranışlar

1. **Bağımsız çıktı tercihleri.** `output-preferences.ts` sayının bütününü okur. Desteklenen ilk-N aralığı 1–999 tam sayıdır; `ilk 1000` artık 100'e dönüşmez, açık `unsupported_output_limit` hatası verir. Sıfır, negatif, kesir ve bilimsel gösterim de reddedilir. Bu sınır görsel kapasite garantisi değildir: kurum 10, AKD/takas 5 gibi mevcut kapasite sınırları ayrıca korunur. Saat/alt not/alış-satış değişiklikleri liste kapsamını sıfırlamaz. Belirtilmeyen alanlar güncel taslaktan devralınır; kapsam belirtilmemişse mevcut ürün varsayılanı korunur. Edit akışı eski tercihleri yeni alanlarla birleştirir. Komut, manuel okuma ve düzenleme hata mesajları destek dışı sınırı açıkça belirtir.
2. **Genel geri alım dipnotu.** `show_footer=false` isteğe bağlı KAP dipnotunu ve hesaplama açıklamasını gizler. Tercih belirtilmediğinde mevcut genel geri alım varsayılanı korunur. Kısmi toplayıcı kapsamı `partial` ile, eksik fiyatlar `missing`/`—` ile temsil edilir; dipnot kapatılsa bile ilgili toplamlar `KISMİ` işaretlidir. Eksiklik/kapsam ayrıntıları kaynak belgesi, tweet ve editör `source_notes` görünümünde kalır. Satır veya tutar uydurulmadı.
3. **Yapılandırma ≠ gönderim.** `/haberfiltre` seçkinin yapılandırılmış olmasını, etkili gönderim durumunu ve istenen/etkili filtre modunu ayrı yazar. Gölge modda açıkça “gönderim kapalı” gösterilir. Gönderim için aktif mod, geçerli hazırlık, seçki enable bayrağı, saatler ve geçerli geçiş zamanı gerekir. Sahibin açık `/secki` isteği otomatik zamanlamayı açmaz.
4. **Sürümlü hazırlık kontrolü.** Yeni `news-readiness.ts`, şirket eşleştirmesi ve resmî kaynak referansları, incelenmiş kapsam hash'i, gerçek insan etiketli örneklem hash'i, sürüm ve sahip incelemesini kontrol eder. Eksik/eski/değişmiş kayıt gölge modda kalır; gerekçe görünür. En az 12 etiket, üç beklenen rota ve eski filtrenin iki tarafı asgari örneklem tabanıdır. Gerçek etiketlerde kritik kaçırma/önemli haberi arşivleme/yanlış kritik hatası varsa geçiş durur. Bu, üretimde başarı ölçüldüğü anlamına gelmez. **Bu çalışmada gerçek üretim etiketlemesi veya hazırlık onayı yapılmadı.** `/golgerapor` salt okunur gerçek inceleme aracı olarak hash'leri, örnek adayları ve mevcut ölçümleri verir; kaydı kendi kendine oluşturmaz. [İnceleme sözleşmesi](news-filter-readiness.md).
5. **Kuyrukta yaş/önem dengesi.** Sadece yeni tarihe göre LIMIT seçimi sürekli akışta eski uygun haberi süresiz geride bırakabilir. İki öncelik yuvası + 10 dakikayı aşan kayıtlar için bir en-eski yuvası kullanılır; yaşlı kayıt yoksa üçüncü yuva da normal öncelik seçimine döner. Aktif modda önemli makro/düzenleme/durdurma/yalanlama önceliği ve doğrulanmış endeks/takip önceliği korunur. Uygunluk ve mevcut teslimat durumu LIMIT öncesinde uygulanır. Tekrar/uncertain korumaları değiştirilmedi.

Seçki kapalıyken belirsiz ama önemli şirket haberlerinin yalnız seçkiye gidip görünmez kalması riski vardır. Bu yüzden bu yapılandırmayla aktifleşme engellenir ve nedeni gösterilir. Başka bir görünür teslim yolu ileride açıkça kararlaştırılmadan sessiz etkinleştirme yoktur. Gölge modun mevcut bildirim filtresi sürer; KAP kapsamı/endeks kuralları değişmedi.

## Regresyonlar ve doğrulama

`test/editor-followup.test.ts` içinde **13 ayrı regresyon**: tam sayı/sınır, saat, dipnot, alış-satış alan bağımsızlığı; kayıtlı tercihlerin edit işine devri; destek dışı komutta iş açılmaması; gerçek geri alım SVG/PNG; gölge mod durum metni; eksik/eski/değişmiş hazırlık, eksik etiket ve gerçek hata ölçümü; seçki kapalı/geçiş zamanı geçersiz durum; gölge ve aktif mod için ayrı sürekli yüksek hacim testleri. `news-readiness-fixture.ts` yalnız izole testlerde sentetik insan inceleme verisi kurar; uygulama bu dosyayı kullanmaz.

Yük testi her mod için 20 eski uygun kayıt ve bir uncertain kayıtla başlar. 40 tur boyunca her tur 8 yeni kayıt eklenir, 3 kart gönderilir. 120 gönderimin tamamı benzersizdir; eski 20 kayıt da gönderilir, uncertain kayıt gönderilmez. Aktif modda her tur ilk iki önizleme kritik haberlerdir. Model işi açılmaz. Dış taşıyıcı sahtedir, saat sabittir/denetimle ilerletilir. Bu bir yük regresyonudur; gerçek Telegram/model performansı ölçümü değildir.

| Kontrol | Sonuç |
|---|---|
| Node 22.22.3, `npm run check` | Geçti |
| `npm test` | **336/336 geçti**, atlanan yok |
| Projenin mevcut `~/Library/Application Support/sector-haber/pdf-venv/bin/python` ile `unittest discover` | **61 test: 60 başarılı, ayrı macOS OCR testi 1 atlandı**; mevcut ortam Python 3.15.0 |
| Ayrı macOS Vision OCR | İlk koşu 30 saniyede timeout; diğer işler tamamlandıktan sonraki tek izole tekrar **1/1 geçti** (15,352 sn). Swift geçici `/tmp/endeks-followup-ocr` dosyasına derlendi; servis dosyaları kullanılmadı. İlk kesintinin kök nedeni kesinleştirilmedi. |
| `npm run build` | Wrangler **dry-run geçti**; deploy yok, model `gpt-6-luna/medium` |
| `npm run kit:export` | Temiz staging, **83 dosya hash'i, 19 örnek PNG** |
| ZIP'i yeniden açma | Tam dosya kümesi/SHA manifesti, transitif kaynak importları, güncel kaynaktan derlenen runtime ile byte eşleşmesi ve 19 PNG boyutu/imzası geçti |
| Gerçek görsel inceleme | Dipnot açık/kapalı genel geri alım, AKD ve 10 satırlı kurum PNG'leri incelendi; eksik hücre ve kısmi toplam işaretleri okunaklı |
| `git diff --check` | Geçti |

ZIP: `exports/ENDEKS-HABER-ChatGPT.zip`

SHA256: `e7a85a38680ce885fe6ebc47aa275eb964522468319f6fb37e350251b9a1a2da`

Python/OCR test kaydı ile dry-run sonucu ayrı değerlendirilmiştir; atlanan OCR testi Python paketinde başarı diye sayılmadı. Uzak CI veya gerçek servis teslimatı çalıştırılmadı.

## Bu takipte değişen dosyalar

- Tercihler ve edit akışı: `src/output-preferences.ts`, `src/bridge.ts`, `src/style.ts`, `src/editorial.ts`, `src/manual.ts`, `scripts/manual_reader.ts`, `src/worker.ts`.
- Görsel ve kapsam bilgisi: `src/report-card.ts`, `src/general-buyback.ts`, `src/types.ts`.
- Haber hazırlığı/durum/kuyruk: `src/news-readiness.ts` (yeni), `src/news-routing.ts`, `src/newsroom.ts`, `src/news-inbox.ts`.
- Testler: `test/editor-followup.test.ts`, `test/news-readiness-fixture.ts` (yeni), `test/news-routing.test.ts`.
- Belgeler/paket: `README.md`, `docs/news-filter-readiness.md`, bu rapor (yeni), `docs/editor-workflow-review.md`, `docs/chatgpt-kit-prompt.txt`, `docs/chatgpt-kit-readme.txt`, `exports/ENDEKS-HABER-ChatGPT.zip`.

Önceki aşamanın diğer değişiklikleri çalışma ağacında korunur. Onaylı gerçek veri incelemesi, canlı geçiş, push ve deploy bu teslimin dışındadır. Geçiş/geri dönüşte önizleme başlangıcı yeni geçiş anına alınarak arşiv replay'i önlenmeli; kuyruk, kaynak ve teslimat makbuzları silinmemelidir. Hazırlık sözleşmesinin ayrıntıları bağlantılı belgede açıklanmıştır.
