# /devrekesici — gerçek kapasite teşhisi

23 Ekim 2026 23:08:48 TRT komutunun canlı isteğinde hata `multi_card_capacity_exceeded`; taslak/teslimat işi oluşmamış. Çalışan kaynak bu inceleme başında `6fd44f3` idi. İstekte liste tercihi yok; bu akışta global tüm-hisseler tercihi okunmuyor.

Hata anının donmuş veri çıktısı saklanmamış. Eklenen fixture, 20:18:04 UTC'deki salt okunur KAP önbelleğinden **komutun kayıtlı zaman sınırıyla yeniden kurulmuş** kamuya açık metaveridir; orijinal hata-anı snapshot'ı veya üretim teslimat makbuzu değildir. Kullanıcı, mesaj/güncelleme kimlikleri, sırlar ve üretim teslimat durumları içermez. Aynı yayın günü, yayın zamanı ve `first_seen <= at` koşulları kullanıldı. 730 adayın ilk görülme aralığı 05:03:29–19:54:12 UTC; tarihlerin tamamı İstanbul günü 23 Ekim'dir.

- 730 farklı bildirim kimliğinin 475'i `Pay Bazında Devre Kesici Bildirimi` başlıklı. Bunların sınıf/türü `DUY/DUY`, her birinde bir hisse var. Diğer 255 bildirim rapora girmiyor.
- Devre kesicilerin yayın aralığı 07:00:04–14:50:42 UTC; 475 farklı kimlik, 400 farklı hisse. Satırlardaki bildirim sayılarının toplamı 475. Bildirim ile şirket sayısı ayrı tutuluyor.
- Normal kısa tweet 161/280 ağırlıklı X karakteri ve geçerli. Bu örneğin reddi tweet sınırından değil, görsel planından geliyor.
- Onaylı günlük rapor düzeni 15 satır/kart; dört kartta 60 hisse. 400 hisse aynı düzende 27 kart gerektiriyor. Kısa tweet seçmek bu görsel sınırını çözmez.

Başlık, tarih ve kod için üç kayıt doğrudan resmî KAP sayfalarıyla da karşılaştırıldı: [1686160 / BLUME](https://www.kap.org.tr/tr/Bildirim/1686160), [1686774 / FORMT](https://www.kap.org.tr/tr/Bildirim/1686774), [1686893 / YGGYO](https://www.kap.org.tr/tr/Bildirim/1686893). Bu örnek kontrolü bütün günün bağımsız yeniden taranması değildir.

## Düzeltme ve sınır

Görsel, tweet ve Telegram açıklama sınırları artık ayrı hata yanıtlarıdır. Yeni başarısız isteklerde kullanılan alan/satır kapasitesi, gereken kart sayısı, bildirim/hisse sayısı, ağırlıklı tweet uzunluğu ve tercihin default/all/first oluşu mevcut `system_state` içinde sayısal teşhis olarak tutulur. Ham kaynak gövdesi saklanmaz. Eski isteklere sonradan geçmiş teşhis yazılmaz; bildirilmiş hata yeniden gönderilmez.

400 hisseyi mevcut dört karta zorlamak, yazıyı küçültmek, otomatik kapsam daraltmak veya thread açmak uygulanmadı. Tam liste için daha yoğun ve ayrıca görsel olarak doğrulanacak yeni bir rapor düzeni ya da kullanıcının açık kapsam kararı gerekiyor. Komutun bu örnekte içerik üretmesi **çözülmüş değildir**. Aynı 400 satırlı veriyle izole uçtan uca test, doğru açıklamayla güvenli durmayı doğrular; başarılı PNG/Telegram teslimatı iddiası değildir. Yeniden denemek tek başına kapasiteyi değiştirmez.

## Doğrulama

- Node 22: check, 388/388 TypeScript testi ve dry-run build başarılı.
- Gerçek günün yeniden kurulmuş 730 aday kaydıyla regresyon: 475/400 ayrımı; tarih sınırı; yinelenen kimliğin sayılmaması; yeni/eski gün örneklerinin elenmesi; default kısa tweet ve açık tüm-kod tweet tercihi; 27 kartlık görsel ret gerekçesi.
- İzole manuel kuyruk: sıfır render, medya yazımı, taslak, model işi, X işi ve teslimat etkisi. Sahte Telegram taşıyıcısında yalnız bir alındı mesajı ve aynı mesajın bir kez güncellenmesi; tekrarda yeni bildirim yok.
- Mevcut Python doğrulama venv'i: 67/67. macOS Vision OCR ayrıca 1/1; geri alım görsel OCR ayrıca 3/3 (bunlar 67 içinde de yer alır).
- ZIP temiz staging'de yeniden üretildi; 97 dosyanın tam hash manifesti, transitif kaynak bağımlılıkları, runtime eşitliği, 20 örnek grubunun 23 PNG'si ve bağımsız dört-sayfa CLI çıktısı doğrulandı. Mevcut render düzeni/font/kapasiteler değişmedi.

ZIP SHA256: `d03cac9443eca930330c92074afd69a2b4774bce8a48121d8cd16b06eaa0c7e9`.

Bu doküman yerel doğrulama kaydıdır. Commit/CI/çalışan sürüm ve yedek makbuzu ayrıca doğrulanır. SQL şeması değişmiyor; yeni sayısal teşhis mevcut tabloyu kullanıyor. Geçiş yalnız haber servisini gerektirir; KAP, panel, model/oturum, shadow filtre ve kapalı seçki korunur. Önceki uygulamaya dönülürse mevcut veritabanı korunur, eski DB canlıya kopyalanmaz. Telegram/X test gönderimi veya eski isteğin yeniden oynatılması yapılmadı.
