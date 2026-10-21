# SECTOR HABER — ayrı KAP toplama hattı

## Doğrulanan sözleşme (21 Ekim 2026)

- Resmî ana sayfanın kendi JavaScript dosyaları `GET_NOTIFICATION_DATA_LIGHT = api/disclosure/list/light` yolunu kullanıyor. `GET https://www.kap.org.tr/tr/api/disclosure/list/light` kimliksiz 200 JSON döndürdü. Bu site içi keşif kaynağıdır; lisanslı MKK API bağlantısı veya sürüm garantili API değildir.
- Detaylar `https://www.kap.org.tr/tr/Bildirim/{id}` üzerinden Accept:text/html ile okunuyor. Güncel örnekler: 1685154 (devre kesici), 1685148 (fon), 1685001 (geri alım), 1685126 (şirket), 1684874 (finansal rapor). Başlangıç kimliği olarak sabitlenmezler.
- Next.js Flight içindeki `disclosureBasic` mevcut. Detay tarihi `YYYY.MM.DD HH:mm:ss`, keşif listesi tarihi `DD.MM.YYYY HH:mm:ss`; ikisi de İstanbul saati. 1685155 kontrol anında HTTP 404 döndürdü; bu sadece o kimliğin o andaki durumudur.
- Endeksler: `https://www.kap.org.tr/tr/Endeksler`; XU030/XU100 içerikleri Flight içinde. Güncel canlı veri üzerinde sayı, kod ve altküme doğrulaması yapılır; eski sabit liste taşınmaz.
- Bir finansal rapor HTML'si yaklaşık 5 MB: eski küçük haber okuyucu sınırı kullanılmaz. KAP için 16 MiB üst sınır ve gövdeyi de kapsayan 12 saniye süre sınırı vardır. Sınır aşımı hatadır.

## Uygulama sırası ve davranış ayrımı

1. Güvenli Flight okuyucu, metadata, İstanbul tarihi, hisse/ilgili hisse ayrımı ve etiketli tablolar.
2. Saf deterministik saklama/gönderim kuralları; varsayılan fon kapalı, diğer önemli şirketler açık, endeks önceliği açık. Pay işlemleri fon-kapalı kontrolünden sonra, başlık istisnalarından önce geçer. BIST 50 kısıtı **yoktur**.
3. Yeni, yalnız KAP'a ait SQLite veritabanı. Kaynak, akış, kuyruk ve cursor tek transaction; kimlik/üyelik benzersizlikleri. RSS/AI tablolarına yazılmaz.
4. Ayrı kalıcı canlı/geçmiş/uzlaştırma/endeks işleri. Eski canlı 3 kayıt, 30 saniye/yoğunlukta 5 saniye; geçmiş 3 kayıt/10 dakika ve sessiz son 24 saat davranışı korunur.
5. Yeni iyileştirme: güncel keşif listesinden başlangıç, bulunamayan kimlikler için kalıcı tekrar deneme ve bağımsız uzlaştırma. Parse/HTTP/erişim hatası 404 değildir; parse hatasında canlı cursor ilerlemez. Başka kimlikler bağımsız uzlaştırmada alınabilir. Sonraki gerçek kimlik görülmüşse 404 boşluğu kayıt altına alınarak tarama ilerleyebilir; boşluk tekrar denenmeye devam eder. Bu durumda cursor “kalıcı olarak hesabı tutulmuş tarama sınırı”dır; bütün önceki kimliklerin geçerli bildirim olduğunu iddia etmez.
6. Devre kesici kayıtları ayrı kuyruk düzenleyicisinde ilk kayıttan 12 saniye sonra, en çok 100 üyeyle sabitlenir. Sınıra ulaşılması beklenmez. Toplayıcının çıktısı teslimata hazır kuyruktur; devre kesici gönderimi kapalıdır.
7. Offline hata/regresyon testleri ve gerçek sayfalarda salt okunur sözleşme kontrolü. İlk aşamada yalnız toplama servisi kuruldu. Sonraki kullanıcı talebiyle aşağıdaki bağımsız Telegram tüketicisi bağlandı; X bağlantısı yoktur; kullanıcı talebiyle tam belgeye dayalı AI üretimi eklenmiştir.

## Sınırlar

Keşif uç noktası değişebilir veya sınırlı bir zaman aralığı gösterebilir. 24 saatlik liste uzlaştırması geçmişin tamamını garanti etmez; kalıcı sıralı cursor ve tekrar denemeler tamamlayıcıdır. Boşluklar silinmez; çözülmeyenler sağlık çıktısında görünür. Endeks erişimi bozulursa son doğrulanan liste ve yaşı gösterilir; ilk doğrulama yoksa endeks önceliği karar üretmez.

Tam metin yalnız `.disclosureScrollableArea` içeriği ve tablolarından çıkarılır. Özet tam metin yerine kullanılmaz. Ek bağlantıları ayrıca döner; PDF içeriği alınmış gibi sunulmaz. Sitedeki erişim kontrolleri aşılmaz, MKK anahtarı kullanılmaz. Haricî teslimat ayrı tüketicide yapılır; `sent_at` başarılı Telegram yanıtında yazılır. Exactly-once teslimat iddiası yoktur.

## Çalıştırma ve işletim

- Kod: `src/kap/`; bağımsız giriş: `scripts/kap_service.ts`.
- Kurulum: `python3 scripts/install_kap.py`. Yalnız `com.sectorhaber.kap` servisini yönetir. Ana Hermes ve haber servisine dokunmaz. KAP'a ayrılmış önceki uygulama kopyası `previous-app` altında tutulur.
- Veriler: `~/Library/Application Support/sector-haber/kap/kap.sqlite`; dosya 0600, klasör 0700, WAL ve foreign key açık, ayrı `SKAP` uygulama kimliği. Yanlış veritabanıyla açılış reddedilir.
- `npm run kap:status`: canlı/geçmiş cursor, son başarı/hata, tekrar deneme bekleyen kimlikler, kuyruk büyüklüğü, endeks yaşı ve keşif kapsamını gösterir. `cursorLagIds` bildirim adedi veya saniye gecikmesi değildir; kimlik farkıdır.
- `npm run kap:probe`: beş güncel türde salt okunur sözleşme testi; çıktı `reports/kap-contract.json`.
- `npm run kap:once -- --db /tmp/sector-kap-check.sqlite`: ayrı veritabanıyla tek toplama turu; hiçbir dış mesaj göndermez.
- `node --import tsx scripts/kap_service.ts --full-text NUMARA`: gerçek detay gövdesi, tablolar, işlem tarihleri, karar tarihleri ve ek bağlantıları. PDF'ler `not_fetched`; eksik gövde `unavailable`, eksik ek listesi `links_incomplete` olarak işaretlenir.
- Tercihler: `kap.preferences.example.json` örneğini düzenleyip `node --import tsx scripts/kap_service.ts --preferences /mutlak/yol/tercihler.json` ile uygula. Şema doğrulanır; devre kesici kapatılınca hazır devre kesiciler susturulur. Tüketici diğer tercihleri de teslimattan önce yeniden değerlendirir. Konular: `dividend`, `buyback`, `financial`, `capital`, `business`, `share_trade`, `circuit`, `other`.
- Canlı, geçmiş ve uzlaştırma ayrı kiralarla korunur. En çok iki eşzamanlı HTTP isteği; tamamı için 12 saniye zaman aşımı. Her canlı/geçmiş/uzlaştırma turunda en çok üç detay isteği. Hatalar 30/60/120/240/300 saniye bekler. Keşif 60 saniyede, endeks başarılı yenilemeden 24 saat sonra çalışır.
- Başlangıçta bulunan kimlik aralığı ve başlangıç zamanından eski yayınlar sessizdir. Başlangıç tarihçesi yalnız 3 kayıt/10 dakika geçmiş işiyle doldurulur; uzlaştırma bu sınırı topluca aşmaz. Geçmiş doldurma bu nedenle yavaştır ve son 24 saat penceresi dışında kalanlar akışa eklenmez.
- Kaynak `disclosures`, kullanıcı akışı `feed`, karar ve teslimata hazır işler `queue/queue_members` tablolarında; filtrelenenlerin kimlikleri `checks` içinde tutulur. Aynı kaynak kimliği ikinci akış veya kuyruk işi üretmez. Farklı düzeltme kimlikleri birleştirilmez.
- Fon özet tercihi ilgili kaydı 19:00 İstanbul zamanına erteleyen `digest` kuyruğu oluşturur. Özet metni hazırlamak/göndermek bu kapsamda yoktur.
- `src/kap-delivery.ts` tüketicisi haber servisi içinde bağımsız döngüdür; en yeni hazır anlık bildirimden başlayarak 5 saniyede bir ilerler. Sessiz başlangıç/geçmiş kayıtları gönderilmez. Hazır kayıtlar sırf RSS yaş sınırından dolayı silinmez.

## Güncel tercih: devre kesici gönderimi kapalı

`circuitNotifications: false` varsayılandır ve eski tercih kayıtlarında alan yoksa da kapalı kabul edilir. Başlık veya özette devre kesici saptanırsa hisse takibi, endeks önceliği ve pay işlemi istisnasından önce gönderim engellenir. Kaynak/akış kayıtları korunur; hazır devre kesici kuyrukları silinmeden `suppressed` yapılır. Henüz kapanmamış gruplar da gönderime kapalı kaydedilir.

Yeni iş ilişkisi, sözleşme, ihale, sipariş, finansal rapor/tablolar ve bilanço `business`/`financial` konularında kalır. Temettü ve önemli sermaye işlemleri de mevcut önemli bildirim kapsamındadır. Rutin fon raporları ve susturulan başlıklar açılmaz. Toplayıcı yalnız kayıt/kuyruk üretir; ayrı Telegram tüketicisi uygun anlık kayıtları teslim eder.

## Telegram tüketicisi

`kap_model_jobs` kuyruk kimliğini haber servisindeki model işiyle ilişkilendirir. KAP kaydı ancak ortak Telegram göndericisi başarılı mesaj kimliği kaydettiğinde `sent` olur. Belirsiz teslimat otomatik tekrarlanmaz. En fazla iki KAP model işi eşzamanlı bekler; hazırlama hataları en fazla üç deneme alır. Toplayıcı, belge okuma/model üretimi ve teslimat bağımsızdır.

Tam HTML metni ve satır/sütun birleşimleri açılmış tablolar okunur. Her resmî dosya eki indirilir; Java byte[] taşıma sarmalayıcısı kod çalıştırmadan doğrulanır. PDF'nin tüm sayfaları ve tabloları çıkarılır. Taranmış sayfalar Apple Vision OCR ile okunur; sayfa görüntüleri hem yazara hem bağımsız denetçiye verilir. Okunamayan/eksik, 20 MB üzeri, 200 sayfa üzeri veya 20 görsel sayfayı aşan belgeler kısmen sunulmaz; incelemeye ayrılır. İşlem tarihi, kurul kararı ve yayın tarihi ayrı tutulur. Geri alım programı gerçekleşmiş işlem gibi yazılmaz.

Bir bildirim tek görsel, tweet ve Kaynağı aç düğmesi olarak gönderilir. Her KAP numarası ayrı olaydır; başlık benzerliği farklı bildirimleri birleştirmez. Model bütçesi haberlerden ayrıdır; abonelik kotası ortaktır. Fon özeti tüketicisi yoktur; fonlar ve devre kesiciler kapalı kalır. `deliveryEnabled` son 60 saniyedeki tüketici kalp atışını gösterir.

## SECTOR yayın odağı

Canlı tercih: endeks üyeliği tek başına gönderim sebebi değildir. Yeni iş, sipariş, ihale, sözleşme/anlaşma; finansal sonuç, bilanço/faaliyet raporu; geri alım ve pay alım/satımı seçili konulardır. Temettü ve sermaye işlemleri korunur. Devre kesici ve fon gönderimi kapalı kalır. `kap.preferences.example.json` bu seçimi içerir; genel kütüphane varsayılanları eski tercih sözleşmesini korur.

Genel özel durum başlıklarında konu özette aranır. Yönetim kurulu/personel değişiklikleri, yönetim bilgi formları ve kredi derecelendirmeleri susturulur. İşlem bildirimlerinin tam metnindeki yönetim kurulu karar tarihi engelleme sebebi değildir. Pay işlemlerinin öncelikli kuralı korunur; BIST 50 sınırı yoktur. Tercih değişikliği bekleyen hazır kuyruğu da yeniden değerlendirir; kaynak kayıtları silinmez, gönderilmiş bildirimler yeniden açılmaz.
