# SECTOR HABER — onaylı deneme sürümü

Aktif sistem Mac mini’de, ayrı `com.sectorhaber.news` servisi altında çalışır.
`@habernewssbot`, sahibinin açık izniyle SECTOR HABER editör botu olarak yeniden kullanılır.
`@Minihermesimbot` gateway’i, ana Hermes ayarları ve eski X hesabı değiştirilmez.

## Korunan / değişen parçalar

- `heranborsahaber` kaynak geçmişi ayrı `sector-haber` dalında korundu; eski kurulum yeniden başlatılmadı.
- Heranborsacode’un **commit edilmiş** ana metin, tablo ve metin yardımcıları `src/reused/` içine alındı. Eski çalışma ağacındaki değişikliklere dokunulmadı.
- Hisse fiyatı, AKD, Terane, kurum dağılımı, eski OAuth/MKK anahtarları ve eski X yayın hedefi taşınmadı.
- Yeni kaynak kaydı, Türkçe editör promptu, kaynak denetimi, marka kartları, olay gruplama ve Telegram onay kuyruğu eklendi.

## Akış

`RSS / resmî PDF → kaynak ve tarih kontrolü → önem filtresi → ortak tam metin okuyucu → olay adayları → Hermes yazım → bağımsız Hermes kaynak denetimi → kesin sayı/birim/kanıt kontrolleri → PNG kart → özel Telegram onayı`

Yazım ve kart metinleri `gpt-6-luna`, `high` ile mevcut Hermes ChatGPT oturumundan hazırlanır.
Araç, MCP, bellek enjeksiyonu, alternatif model ve ücretli API sağlayıcısı kapalıdır.
Oturum yenilemesini Hermes’in kendi kilitli kimlik çözümleyicisi yapar; tokenlar kopyalanmaz veya Cloudflare’a aktarılmaz.
Üyeliğin kota sınırları geçerlidir. Bir aday en fazla bir kaynak denetimli düzeltme turu alır.

Sayı denetimi İngilizce/Türkçe ondalık ve binlik ayırıcıları, milyon/milyar ölçeklerini ve para birimini kayan nokta hesabı olmadan karşılaştırır.
Bu denetim haberin dış dünyada kesin doğru olduğunu kanıtlamaz: resmî kaynak, çoklu kaynak ailesi veya tek kaynak aktarımı ayrı belirtilir.
Eksik/çelişkili kanıtlar, belirsiz galeri/PDF veya doğrulamadan geçmeyen metinler kullanıcıya tamamlanmış haber gibi gönderilmez.

## Kaynak kaydı

`sources.json` ortak kayıttır. Sağlık, etag, son başarılı kontrol ve hata bekleme süreleri ayrı veritabanında tutulur.
Kaynaklar tek tek `sources.candidates.json` ve `reports/source-check.json` üzerinden doğrulanmıştır.
Kurulumda eski RSS arşivi canlı kuyruğa boşaltılmaz; başlangıç anı ve kısa zaman payı kaydedilir. Önem ve güncellik birlikte sıralanır.
İlk denemede günlük en fazla 60 model adayı ve aynı anda 12 bekleyen onay kullanılır; bu sayılar X otomatik yayını açmaz.
NTV’nin denenen RSS’i ve TCMB’nin özel PPK beslemesi eski kaldığı için etkinleştirilmedi. PPK basın duyuruları genel TCMB basın akışından takip edilir.
TÜİK RSS adayı 404, güncel veri portalı ise otomatik istemciye koruma sayfası verdi; bültenler okunmuş gibi sisteme eklenmedi.
KAP, haberlerin kendi metninde verilen resmî bildirim bağlantılarından birincil kaynak olarak okunur; lisanslı API veya varsayılan sayısal bildirim taraması kullanılmaz.
SPK’nın güncel bülten listesi ve PDF’leri ayrı okuyucuyla takip edilir; sayfa ve tablo sınırları korunur.

Kamuya açık RSS veya okunabilir sayfa, yeniden yayın/görsel lisansı sayılmaz.
Kaynaklar özel editöryal değerlendirme ve özgün, atıflı olgular için kullanılır. Yayıncı fotoğrafları alınmaz.
Bloomberg HT, TRT, CNBC-e, BBC vb. kullanım koşulları kayıt altındadır; doğrudan içerik çoğaltımı ve lisans gerektiren kullanım izni varsayılmaz.

## Telegram ve X güvenliği

- Yalnız sabit kullanıcı kimliği + özel sohbet eşleşmesi işlem yapabilir.
- Onay, ret, kaynakla yeniden denetlenen düzenleme ve bir saat erteleme desteklenir.
- Tekrarlanan/eski düğmeler sürüm kontrolünden geçemez.
- Fotoğraf, Telegram’a PNG dosyası olarak yüklenir; link önizlemesi değildir.
- Belirsiz gönderim zaman aşımı otomatik tekrar edilmez; çift kart oluşturulmaz.
- **Bu sürümde X’e gönderim yapan kod yoktur.** Onay yalnız kayıt oluşturur; sonraki sürümde eski onaylar kendiliğinden yayımlanmaz.

## Kurulum ve işletim

Gizli bilgiler repo dışında, `~/Library/Application Support/sector-haber/secrets.json` içinde `0600` izinle saklanır.
Çalışma kodu `.../sector-haber/app`, veritabanı `sector-haber.sqlite`, medya `media/` altındadır.
SQLite’ın uygulama kimliği `SECT` olarak sabittir; başka uygulama veritabanı açılmaz.
Kaynakların tam metin geçici kaydı 24 saatle sınırlıdır; kanıt pasajları onay kaydıyla korunur.

```sh
npm ci --ignore-scripts
npm run check
npm test
python3 -m unittest discover -s test -p 'test_*.py'
npm run build
python3 scripts/install_local.py
```

Güncelleme: `python3 scripts/install_local.py --update`. Yalnız SECTOR servisi durdurulur.
Durdurma: `launchctl bootout gui/$(id -u)/com.sectorhaber.news`.
Ana Hermes gateway’i ve başka proje servisleri bu komutlara dahil değildir.

## Cloudflare

Yeni ve ayrı Worker `sector-haber-review`, D1 `sector-haber-db`, R2 `sector-haber-media` oluşturuldu.
Genel `workers.dev` / `pages.dev` ulaşımında TLS/erişim sorunu doğrulandığı için aktif yayın akışı bu adrese bağlanmaz.
Cloudflare cron kapalı ve `MODE=dry_run` durumundadır. Aynı pipeline D1/R2 adaptörleriyle burada da çalışabilecek şekilde korunur.
API anahtarı / ChatGPT oturumu buluta aktarılmaz. Yeni X hesabının canlı yayını sahibinin ayrıca açık onayını bekler.

Instagram projesi kullanıcının ek talebiyle kaldırıldı: Worker, workflow, D1 ve 69 dosyalı R2 deposu silindi. `evb-temp` korundu.

## Doğrulamalar

`npm test` XML/Atom, yönlendirme güvenliği, tam metin, kaynak kimliği, sayısal ölçek/para birimi, kanıtlar, olay tekrarları,
beş PNG şablonu, Telegram yetkisi/onayları, SQLite işlemleri, iş kiralama ve tekrar sonuç teslimini test eder.
Gerçek haber denemeleri `scripts/demo.ts`, erişim raporları `reports/` içindedir. Ham yayıncı metinleri/görselleri Git’e eklenmez.
