# SECTOR HABER — Telegram haber masası

Aktif sistem Mac mini’de, ayrı `com.sectorhaber.news` servisi altında çalışır.
`@habernewssbot`, sahibinin açık izniyle SECTOR HABER editör botu olarak yeniden kullanılır.
`@Minihermesimbot` gateway’i, ana Hermes ayarları ve eski X hesabı değiştirilmez.

## Korunan / değişen parçalar

- Aktif SECTOR HABER kodu `heranborsahaber` reposunun `main` dalında, `sector/` dizinindedir. Eski kod arşiv olarak korunur; eski kurulum yeniden başlatılmadı.
- Heranborsacode’un **commit edilmiş** ana metin, tablo ve metin yardımcıları `src/reused/` içine alındı. Eski çalışma ağacındaki değişikliklere dokunulmadı.
- Hisse fiyatı, AKD, Terane, kurum dağılımı, eski OAuth/MKK anahtarları ve eski X yayın hedefi taşınmadı.
- Yeni kaynak kaydı, Türkçe editör promptu, kaynak denetimi, marka kartları, olay gruplama ve Telegram içerik kuyruğu eklendi.

## Akış

`RSS / resmî PDF → kaynak ve tarih kontrolü → önem filtresi → Telegram başlık/özet → sahibin oluştur düğmesi → ortak tam metin okuyucu → olay adayları → Hermes yazım → bağımsız Hermes kaynak denetimi → kesin sayı/birim/kanıt kontrolleri → PNG kart → tek fotoğraflı Telegram mesajı`

Yazım ve kart metinleri `gpt-6.1-sol`, `low` ile mevcut Hermes ChatGPT oturumundan hazırlanır.
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
Günlük en fazla 240 model adayı ve aynı anda en fazla 12 teslim edilmemiş taslak kullanılır. Teslim edilmiş içerikler yeni haberleri durdurmaz. X yayını kalıcı olarak kapsam dışıdır.
NTV’nin denenen RSS’i ve TCMB’nin özel PPK beslemesi eski kaldığı için etkinleştirilmedi. PPK basın duyuruları genel TCMB basın akışından takip edilir.
TÜİK RSS adayı 404, güncel veri portalı ise otomatik istemciye koruma sayfası verdi; bültenler okunmuş gibi sisteme eklenmedi.
Haber okuyucusu KAP bağlantılarını birincil kaynak olarak okuyabilir. Ayrıca bağımsız KAP toplayıcısı çalışır; kalıcı cursor, saklama ve kuyruk kuralları [KAP.md](KAP.md) içindedir. Devre kesici gönderimi kapalıdır; KAP kuyruğu haber servisindeki bağımsız Telegram tüketicisine bağlıdır.
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
- **X yayını kalıcı olarak yoktur.** X hedef ayarı ve yayın hazırlığı kaldırılmıştır. Eski onay düğmeleri yalnız yerel taslak durumu değiştirir; yayın kaydı oluşturmaz.

## Kurulum ve işletim

### MacBook üzerinden geliştirmeye devam

`main` dalını çekip `sector/` altında geliştirme ve test yapılabilir. Canlı haber ve KAP servisleri Mac mini'de çalışır; Git pull/push canlı servisi kendiliğinden güncellemez.
MacBook'ta kurulum scriptlerini veya `local_service.ts` dosyasını çalıştırmak ikinci bir bot tüketicisi başlatabilir. Geliştirme için aşağıdaki kurulum komutlarından yalnız bağımlılık, kontrol, test ve build adımlarını kullan; canlı kurulum Mac mini'de yapılır.
Gizli bilgiler, Hermes oturumu, canlı SQLite veritabanları ve medya Git ile taşınmaz. Mevcut canlı servislere erişim olmadan dağıtım yapılmış gibi raporlanmamalıdır.

Güncel kararlar: X yayını yok; Telegram'da tek fotoğraf + tweet açıklaması + Kaynağı aç ve Düzenle düğmeleri; model `gpt-6.1-sol` / `low`, mevcut Hermes ChatGPT oturumu; kodla üretilen 1080×1350 lacivert/gri kartlar. Ana Hermes gateway'i ve diğer projeler değiştirilmez.

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
API anahtarı / ChatGPT oturumu buluta aktarılmaz. X yayını planlanmaz; hiçbir onay veya ayar X gönderimi açmaz.

Instagram projesi kullanıcının ek talebiyle kaldırıldı: Worker, workflow, D1 ve 69 dosyalı R2 deposu silindi. `evb-temp` korundu.

## Doğrulamalar

`npm test` XML/Atom, yönlendirme güvenliği, tam metin, kaynak kimliği, sayısal ölçek/para birimi, kanıtlar, olay tekrarları,
beş PNG şablonu, Telegram yetkisi/onayları, SQLite işlemleri, iş kiralama ve tekrar sonuç teslimini test eder.
Gerçek haber denemeleri `scripts/demo.ts`, erişim raporları `reports/` içindedir. Ham yayıncı metinleri/görselleri Git’e eklenmez.

## Ayrı KAP toplama hattı

KAP bildirimleri için ayrı cursor, kurallar, kalıcı kayıt ve kuyruk uygulaması: [KAP.md](KAP.md). Toplayıcı ayrı kayıt/kuyruk üretir; tüketici tam metin, tablolar ve PDF eklerini doğrulanmış taslak üretimine aktarır.

## Tek mesaj ve sade kartlar

Haberler önce metin önizlemesi olarak gelir. Sahibin istediği taslak bir PNG ve açıklamasındaki tweet metniyle tek Telegram mesajıdır. KAP bu taslağı otomatik hazırlar. Kaynak, önem puanı ve teknik durum için ikinci mesaj gönderilmez. “Kaynağı aç” birincil belgeyi açar; “Düzenle” kaynak denetimli revizyon ister. Yeni biçimde teslim edilmiş bir taslağın revizyonu aynı fotoğraflı mesajı günceller. Eski iki mesajlı geçmiş silinmez.

Telegram fotoğraf açıklamasının teknik sınırı 1024 UTF-16 karakterdir. Başlık/gövde/etiketler bu sınırı aşarsa Hermes aynı sınırlı düzeltme turunda anlamı koruyarak yeniden yazar ve tekrar denetlenir. Metin kesilmez, ikinci mesaja bölünmez; sığmayan doğrulanmamış sonuç gönderilmez. [Telegram sözleşmesi](https://core.telegram.org/bots/api#sendphoto).

1080×1350 kartlarda yalnız marka, güçlü başlık ve kısa açıklama bulunur; gerçek son dakika şablonunda küçük bir konu etiketi vardır. Tarih, kullanıcı adı, kaynak listesi, yan şeritler, puan ve DENEME filigranı kaldırılmıştır. Renkler ve onaylı logo korunur; başlık boyutu ve satır yerleşimi metne uyarlanır, taşma sessizce kesilmez.

## Akış kapasitesi ve KAP teslimatı

Kaynak filtresi 60 puan ve üzeri ekonomi/şirket adaylarını toplar; haber üretimi artık yalnız sahibin isteğiyle başlar; açıkça istenen taslakta ek bir önem puanı engeli uygulanmaz. Kaynak denetimi, sayı/kanıt kontrolleri ve çözümlenmemiş belirsizlik engeli korunur. Günlük 240 model adayı sınırı teslim edilmiş mesaj sayısı değildir; başarısız adaylar da bu bütçeyi kullanır. ChatGPT kota sınırında otomatik bekleme devam eder.

Haber teslimatı kaynak taramasından ayrı 10 saniyelik döngüde çalışır. KAP tüketicisi tam metni, tabloları ve tüm PDF eklerini okur. Taranmış ekler OCR ve sayfa görüntüsüyle modele ve denetçiye iletilir. Eksik/okunamayan ek varsa özetten taslak üretilmez. KAP için ayrı günlük model bütçesi uygulanır; aynı Hermes abonelik kotası paylaşılır. Telegram'a bir görsel, tweet metni ve Kaynağı aç düğmesi tek mesajda gelir.

## Kendi haberini gönder

@habernewssbot özel sohbetine desteklenen kaynaklardan haber bağlantısı, KAP bağlantısı, PDF dosyası veya en az 100 karakterlik haber metni gönder. Yalnız kayıtlı hesap sahibi kabul edilir. Aynı kaynak denetimi ve görsel üretimi uygulanır; X yayını yoktur. @Minihermesimbot genel Hermes sohbetidir. Bilinmeyen sitelerde tam metni veya PDF'yi gönder. Dosya/metin taslaklarının kaynak düğmesi orijinal Telegram gönderisini açmak için bot bağlantısını kullanır.

## Haberler: önce önizleme, sonra istek üzerine üretim

RSS ve SPK haberleri önce kaynak adı, başlık ve kaynak özetiyle Telegram'a gelir. Bu aşamada model çağrısı, görsel üretimi ve AI bütçe rezervasyonu yapılmaz. `Tweet ve görsel oluştur` düğmesi yalnız kayıtlı sahibin özel sohbetinde çalışır. Basıldığında tam kaynak okunur; aynı kanıt/denetim ve tek fotoğraflı taslak akışı çalışır. Tekrarlanan tıklamalar aynı işi kullanır. Çok benzer başlıklar 6 saatlik pencerede ilk iki sözcük ve rakamlar eşleşiyorsa kota harcamadan gruplanır; farklı rakamlı gelişmeler korunur. Anlamı aynı fakat başlığı farklı haberler yine gelebilir; otomatik model harcaması yapmazlar.

KAP'ın otomatik belge/PDF okuma ve üretim akışı ile sahibin doğrudan gönderdiği haberler değişmez. Eski otomatik haber işlerinin bekleyenleri geçişte silinmeden duraklatılır. Yeni kurulumda önceki bütün haberleri bildirim olarak yığmamak için önizleme başlangıcı ayrıca saklanır. İstekler ayrı 5 saniyelik döngüde hazırlanır. Geçici Telegram belirsizlikleri otomatik yeniden gönderilmez.

## Tweet dili ve etiketler

Tweet ve görsel metninde yayıncıya atıf veya Kaynak satırı kullanılmaz; kaynak düğmede kalır. İddia, plan, koşul ve açıklama sahibinin kimliği korunur. BIST şirket haberleri ve doğrulanmış hisse kodlu KAP bildirimlerinde `#Borsa #BIST #HİSSEKODU` kullanılır. Kod kurum kısaltmasından tahmin edilmez. Birden fazla şirket/kod varsa iki piyasa etiketi ve ilgili konu etiketi seçilir; yabancı şirket haberlerine BIST etiketi eklenmez. Diğer haberlerde doğrudan ilgili 2–3 şirket/konu etiketi kullanılır. Yazım kuralı ihlali mevcut sınırlı düzeltme/denetim turuna girer; kaynak delilleri değiştirilmez.

Kartlarda lacivert zemin/açık alt panel ile açık zemin/lacivert alt panel, haber türünden bağımsız yaklaşık eşit olasılıkla seçilir. Seçim ilk hazırlamada saklanır; yeniden denemede ve taslak düzenlemesinde korunur. Mevcut kartların renkleri değiştirilmez. Bu seçim AI çağrısı gerektirmez.

Tweet başlığı tek bir uygun emojiyle başlar (varsayılan 📢, gerçekten acil gelişmelerde 🚨). Gövde, etiketler ve görsel metninde emoji bulunmaz. Eksik başlık emojisi ek model çağrısı olmadan tamamlanır; yanlış yerleşim mevcut sınırlı düzeltme turunda ele alınır.
