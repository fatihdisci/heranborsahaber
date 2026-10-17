# Canlı haber ve isteğe bağlı tweet akışı

Kaynak kataloğunda 17 haber akışı/X hesabı tanımlıdır. 6 Ekim 2026'daki son ayarda Investing Türkiye kapatılmış, 16 kaynak etkin bırakılmıştır: 12 haber/resmî akış ve 4 X hesabı. Ayrıntılı aday/engel listesi: reports/SOURCE_AUDIT.txt; önceki gerçek erişim ölçümleri: reports/public-source-expansion.json.

6 Ekim 2026 güncellemesi: Haber bildirimi ile tweet hazırlama ayrıldı. Kurulu sistemde 12 haber/resmî feed ve 4 X hesabı aktiftir (Investing kapalı). Dağıtım `sources.yaml` dosyasında bütün kaynaklar yine güvenli varsayılan olarak kapalıdır.

1. Yeni ve filtreden geçen haber, başlık/özet/kaynak bağlantısıyla özel Telegram sohbetine gönderilir. Bildirim için ikinci kaynak veya model yanıtı beklenmez.
2. Karttaki **Tweet oluştur** düğmesi yalnız kayıtlı özel kullanıcı, özgün kartın mesaj kimliği ve kaydın içerik hash'i eşleştiğinde çalışır. Bu aşamada kaynak metni okunur ve Hermes'e iş gönderilir. Kendiliğinden tweet oluşturma/model çağrısı yoktur.
3. Hazırlanan taslak tek mesaj olarak gelir. 7 Ekim düzeltmesiyle haber sayfasının kendi ana görseli Telegram'a gerçek fotoğraf dosyası olarak yüklenir; tweet aynı mesajın açıklamasıdır. Kaynak sayfası tek düğmeyle açılabilir. Bu özel kaynak önizlemesi yeniden yayınlama izni sayılmaz. Haberde fotoğraf yoksa uygun ve izinli kurum arşivi, o da yoksa sade tweet metni kullanılır. Ayrı teknik rapor veya Commons adayları gönderilmez. X'e otomatik yayın yoktur.

Filtre, haber başlığı ve RSS özetinde Türkiye'ye veya yerli kurum/piyasa/şirkete doğrudan bağ arar; sinyaller OR mantığıyla değerlendirilir. Tek başına genel Fed, altın veya petrol başlığı geçmez. SPK haberleri elenmez; KAP'taki rutin geri alım/pay işlemleri ve açık yatırım tanıtımları elenir. SPK bültenleri için doğrudan site/PDF okuyucusu yoktur; medya kaynaklarının SPK haberleri alınır.

X hesapları: **@ismailsaymaz, @haskologlu, @abakingurlek, @rterdogan**. Eski repodaki gibi nitter.cf'nin herkese açık RSS akışları okunur; her hesap 3 dakikada bir kontrol edilir. Sadece o hesaba ait, geçerli tarihli kendi paylaşım metni işlenir. Başka hesap retweetleri, yanıtlar ve alıntılanan hesabın metni kendi paylaşımı gibi değerlendirilmez. İlk başarılı tarama sessiz başlangıç oluşturur; geçmiş X paylaşımları topluca gönderilmez. Relay erişimi kesilirse kaynak sağlığı hata gösterir; kesintisiz X erişimi garanti edilmez. X oturumu/cookie/API anahtarı kullanılmaz; X yayın erişimi yoktur. Broker yalnız bu dört /hesap/rss yoluna izin verir.

Canlı bildirimlerde yayın saati biliniyorsa 30 dakika tazelik sınırı vardır; gönderim sırasında da kontrol edilir. Kullanıcının bugün gönderilmiş bir karttan sonradan istediği tweet, özgün yayın tarihini koruyarak 30 dakikalık iş süresiyle hazırlanabilir; 24 saatten eski olay güncel diye işlenmez.

Tek haber kaynağından istenen taslak, **kaynak aktarımı** olarak açık atıfla hazırlanabilir; bağımsız teyit edilmiş haber diye sunulmaz. X taslağı yazarın birebir desteklenen ifadelerini alıntılayarak sunar. Model, dayanağı olmayan cümle/sayı ekleyemez. Tam metin okunamaması veya doğrulama hatası halinde taslak yerine hata bilgisi gelir. Kaynak kartları model sorunlarından bağımsız devam eder.

Investing Türkiye kapalıdır: yeni kart üretmez ve eski Investing kartlarının düğmesiyle taslak başlatılamaz. Etkin başlıca kaynaklar Foreks, Bloomberg HT, CNBC-e, Habertürk, Sözcü, Dünya, Ekonomim, NTV Para, TRT Haber Ekonomi, Anadolu Ajansı Ekonomi, Euronews Türkçe ve TCMB'dir. Foreks/Bloomberg HT 60 saniye; Habertürk/Sözcü/Dünya/Ekonomim 120 saniye; diğer RSS ve TCMB akışları 180 saniyede bir taranır. Dört X hesabı 180 saniyede bir kontrol edilir.

Komutlar: `/haber_kaynaklar`, `/haber_filtre`, `/haber_durum`, `/haber_butce`, `/haber_durdur`, `/haber_baslat`.

Yeni habnews uygulamasının dört container'ı güncellendi; mevcut Hermes ve Her An Borsa kaynaklarına/servislerine dokunulmadı. Mac açık ve çevrimiçi kalmalıdır. Kaynak taraması ve Telegram teslimi birkaç saniye gecikme yaratabilir; saniyelik yayın takibi iddiası yoktur.

Önceki doğrulama: 160 test geçti. Kaçırılan Foreks/Cevdet Yılmaz haberi yeni botta kabul edildi. Gerçek kullanıcı düğmesinden bir Bloomberg HT taslağı, biçim düzeltmesinden sonra gerçek Hermes ile üretildi; kaynak atıflı gövde ve onay kartının Telegram teslimi doğrulandı. Model biçim hatalarında aynı kullanıcı isteği en fazla iki ek düzeltme alır; her çağrı mevcut günlük/olay bütçesine sayılır.

Düğme düzeltmesi: İşlem sürerken tekrar basış yeni model çağrısı yapmaz. Hazır taslak varsa aynı metin geri verilir. Başarısız veya reddedilmiş taslakta kullanıcı yeniden basarsa yeni sürüm oluşturulur; eski onaylar geçersiz olur. Geçmiş isteğin hata bildirimi yeni sürüm başladıktan sonra gönderilmez.

## Sade taslak düzeltmesi

177 test geçti. Okuyucu yalnız seçilen haberin başlık ve ana metin alanını kullanır; öneriler, menüler ve sonraki haberler dışarıda kalır. Foreks, Bloomberg HT, Habertürk, Sözcü, Dünya, Ekonomim ve TCMB gerçek sayfalarında metin okuma doğrulandı. Türkçe sayı ifadeleri (455 bin 578, 1 milyon) doğrulanır. Eşzamanlı model işi beklemek hata değildir. Süresi dolmuş geçici metin yeniden okunur. Teknik olaylar yerel kayıtta tutulur.

Ana konusu Karahan olan ve TCMB bağlamı doğrulanan haberler için TCMB'nin resmî Flickr arşivinden kullanım izni açık kurum toplantısı fotoğrafı doğrulandı; isim eşleşmesinden kişinin fotoğrafta bulunduğu sonucu çıkarılmaz; bu fotoğraf olayın güncel görüntüsü olarak sunulmaz. 7 Ekim'den itibaren öncelik haberin kendi görselindedir; kurum arşivi yalnız uygun yedektir. Investing kapalı kalır.

Tweet biçimi: Doğrulanmış başlık/olgulara göre 2–3 konu etiketi eklenir. 📢 yalnız başlığın önünde kullanılır; konu kelimelerinden aciliyet çıkarılarak 🚨 eklenmez. Metin sonuna emoji eklenmez ve ölüm haberlerinde emoji kullanılmaz. Kullanıcının istediği taslak en fazla 380 karakterdir. Modelin kanıt denetimi öncesi gövdesi değişmez; süslemeyi uygulama sonradan ekler. Bu bölümün ilk sürümünde 219 test geçti.


## İçerik ve teslimat sağlamlaştırması — 6 Ekim 2026

Kaynak URL'si, canonical URL, başlık, seçilen ana metin ve iş dosyasının özeti birbirine bağlanır. Birden çok haber bloğunda doğru haber seçilemiyorsa metin modele verilmez. Menü, öneri, etiket, dipnot ve fotoğraf kredileri metinden ayrılır. Olgu cümlesindeki koşul, iddia, yalanlama ve atıf bölümleri kırpılamaz. Yeni haber taslakları başlık, kaynak, emoji ve etiketler dahil en fazla 380 karakterdir; eski kayıtlar ve sosyal gönderi sözleşmesi 550 sınırını korur.

Tek bir haberin biçim/kanıt hatası bütün model akışını durdurmaz. Biçim hataları sınırlı sayıda düzeltilir; kaynaktaki gerçek belirsizlik uydurma metinle kapatılmaz. Süresi geçen iş rezervasyonları serbest bırakılır; sonucu belirsiz çağrı otomatik tekrarlanmaz.

Fotoğrafın dosya özeti gönderim öncesinde yeniden doğrulanır. Telegram açıklaması fotoğrafın üstünde gösterilir. Fotoğraf kesin olarak reddedilirse veya dosya bütünlüğü bozuksa aynı teslimat sade taslak metnine döner; teknik çıktı gönderilmez. Teslim sonucu belirsiz ağ kesintisinde çift mesaj riski nedeniyle otomatik ikinci gönderim yapılmaz.

6 Ekim temel sürümünde 219 otomatik test geçti. 28 gerçek URL örneğinin 25'inde metin çıkarma ve Collector→AI iş girdisi bağlantısı doğrulandı; bir galeri belirsiz gövde nedeniyle durduruldu, iki Investing sayfası HTTP 403 verdi. Üç gerçek model denemesinde 205, 301 ve 294 karakterlik taslaklar doğrulandı; bir biçim hatası ikinci çağrıda düzeldi. Kayıt: `reports/HARDENING_AUDIT.json`.

## Gerçek fotoğraf teslimi — 7 Ekim 2026

Kaynak görseli yalnız aynı haberin `og:image`, `twitter:image`, haberle URL bağı doğrulanmış JSON-LD veya seçilmiş haber içindeki görsel alanından alınır. Menü, reklam, logo ve diğer haber görselleri kullanılmaz. Hostlar önceden belirlenir; sayfa yeni ağ yetkisi veremez. Public DNS/HTTPS/redirect, 10 MB indirme sınırı, MIME/magic, decode/piksel ve boyut kontrolleri uygulanır. Fotoğraf kaynak ana metin digest'iyle bağlanır. Dosya JPEG olarak normalize edilir; Telegram'a multipart `sendPhoto` ile yüklenir ve tweet açıklaması üstte gösterilir. Görsel bulunamazsa bağlantı önizlemesi yerine yalnız metin gelir.

Özel sohbet önizlemesinin kaydı yeniden yayınlama izninden ayrıdır: `private_source_preview`/`unknown`. Bu dosya yeniden kullanım hakkı doğrulanmış medya diye export edilmez. Hakları doğrulanmış arşiv yolu korunur. Görsel indirme denemesi üç aday ve yaklaşık 20 saniye ile sınırlıdır; erişim engeli aşılmaz.

237 otomatik test geçti; yanlış haber/görsel eşleşmesi, yabancı CDN, bozuk dosya, WEBP dönüşümü, fotoğraflı tek mesaj, özel sohbet sınırı, multipart upload ve yayınlama paketinde hak ayrımı doğrulandı. Canlı kaynak örnekleri ve mevcut taslağın aynı mesajdaki fotoğraf düzeltmesi: `reports/PHOTO_DELIVERY_AUDIT.json`.

## Editoryal iyileştirmeler — 17 Ekim 2026

`source-grounded-v3` aylık/yıllık dönem, beklenti/gerçekleşme ve yüzde/yüzde puan ayrımlarını ortak bot ve kopyalama talimatlarında açıklar. Cari denge, bütçe, temettü ve kredi haberleri özel konu etiketleri alır. Konu kelimeleri olayın aciliyetini kanıtlamadığından iflas, tasfiye veya faiz kararı haberlerinde otomatik 🚨 kullanılmaz.

380 karakteri aşan manuel haber taslağında seçilmiş tam kaynak cümlesi başlık olarak denenir; aynı cümlenin gövdede tekrar gösterilmesi engellenir. Bütün olgular, sayılar, koşullar ve kaynak atfı korunur; tüm doğrulamalar yeniden çalışır. Metin hâlâ sığmıyorsa olgu silinmez, mevcut sınırlı model düzeltme akışı sürer. Sosyal paylaşım sözleşmesi bu otomatik kısaltmaya dahil değildir.

Önceki editoryal sürümle oluşturulmuş taslak, kullanıcı karta yeniden bastığında güncel kurallarla hazırlanır. Değişiklikler MacBook'ta 450 çevrimdışı testle doğrulandı; canlı model veya Telegram denemesi yapılmadı. Mac mini'deki runtime'a uygulanması ayrıca gerekir; depodaki kodun değişmesi canlı kurulumu güncellemez.

## Haber editörü v4 — yerel geliştirme

Bu bölüm `source-grounded-v4` kodunu anlatır; canlıya dağıtım kaydı değildir.

1. **Haber türleri:** faiz, enflasyon, cari denge, bilanço, temettü, şirket gelişmesi ve iddia/yalanlama için farklı bilgi öncelikleri vardır. Bot ve GPT’ye aktarım aynı kuralları kullanır. Tür seçimi metin tabanlı bir yönlendirmedir; eksik dönem, beklenti veya tutar üretmez.
2. **Kontrollü yeniden yazım:** olgular önce mevcut birebir kaynak denetiminden geçer. Gösterim sırasında yüzde yazımı kısalabilir; yalnız tam eşleşen faiz kararı, imzalanmış sözleşme ve planlanan yatırım açıklamalarında dar dil kalıpları sadeleştirilir. Kaynak cümlesi metadatada saklanır. Alıntılar, yüzde puan birimi ve kalıba uymayan koşul/yalanlama cümleleri korunur. Serbest model paraprazı kabul edilmez.
3. **Düzenleme düğmeleri:** yeni manuel haber taslaklarında Kısalt, Daha sade, Başlığı değiştir ve Etiketleri kaldır bulunur. Her işlem kullanıcı/özel sohbet/mesaj/hash/sürüme bağlıdır. Önce doğrulanmış mevcut olgularla modelsiz düzenleme denenir; gerekirse aynı kaynak üzerinden bütçeye tabi model işi açılır. Kısalt sonucu gerçekten daha kısa; başlık değişikliği gerçekten farklı olmalıdır. Yeni sürüm eski onayı geçersiz kılar. Hiçbir düğme X’te yayın yapmaz. Fotoğraf gönderimi metne dönerse düğmeler korunur.
4. **Tekrar ve güncelleme:** farklı yayıncıların birebir aynı normalize başlık ve tam özetleri, 30 dakikalık zaman penceresinde tek kartta kaynak bağlantılarıyla gruplanabilir. Kısa/belirsiz özetler ve sosyal hesaplar birleştirilmez. Farklı rakam veya anlatım ayrı kalır; bu muhafazakâr eşleştirme bütün anlamsal tekrarları yakalamaz. Aynı kaynak URL/kimliğinin başlığı veya özeti değişirse yeni kart önceki metni açıkça etiketler. Gruplama bağımsız teyit sayılmaz.
5. **Hata ve devam:** kaynak erişim engeli, zaman aşımı, ayrıştırma, model oturumu/kotası ve doğrulama hataları sade mesajlarla ayrılır. Yeniden dene düğmesi başarısız aşamayı açık kullanıcı isteğiyle başlatır; eski sürüm, yanlış kullanıcı/mesaj ve eşzamanlı tekrar engellenir. Teslimi belirsiz Telegram mesajı otomatik tekrar gönderilmez. Model düzeltmesi geçerli kaynak önbelleğini yeniden kullanır; süresi geçmiş veya özeti uyuşmayan metin yeniden okunur. Mevcut en fazla iki otomatik biçim düzeltmesi ve bütçe sınırları korunur.
6. **Kalite ölçümü:** `python -m habnews.quality --output reports/editorial-quality.json` on sabit örnekte kaynak doğrulaması, kritik dönem/koşullar, sayılar, tekrar ve uzunluk ölçer. Dokuz örnek sentetik; biri 13 Ekim CNBC-e haberinin arşiv cümlesidir. Varsayılan koşu referans taslakları kullanır, model çağırmaz ve okunabilirliğin insan değerlendirmesinin yerini tutmaz. `--results DOSYA` ile `{ "rate": {"result": ... , "run_metadata": {"turns": 1}}, ... }` biçimindeki kaydedilmiş model çıktıları değerlendirilebilir; `--baseline ÖNCEKİ_RAPOR` karşılaştırma ekler. Eksik örnek başarısız sayılır. `/haber_kalite` son yedi günlük taslak uzunluklarını, modelsiz düzenlemeleri, gruplanan kartları, biçim düzeltmelerini ve yerel model çağrılarını gösterir; hesabın toplam kotasını bildirmez.

Manuel işlerin tam kaynak önbelleği mevcut beş dakikalık son kullanma süresi boyunca tekrar kullanılabilir. Collector süresi dolan dosyaları 30 saniyelik temizlik aralığında kaldırır; yedeklere tam kaynak metni eklenmez. Otomatik işlerin metni tamamlanınca silinir.

### Mac mini dağıtım kontrolü

Mevcut runtime, kaynak ayarları, veritabanı, gizli dosyalar ve OAuth oturumu korunmalıdır. Veritabanını yedekleyip aktif model işinin bitmesini bekleyin; çalışan collector ve approval süreçlerini güncelleme sırasında aynı kod sürümünde tutun. Yeni tablolar (`habnews_feed_group`, `habnews_job_failure`, `habnews_retry_callback`) açılışta idempotent olarak eklenir; eski tablo verileri silinmez. Collector/approval ve runner image’larını güncel kodla yeniden derleyin; paket `sources.yaml` dosyasını canlı etkin kaynak ayarlarının üzerine yazmayın.

Dağıtımdan önce `python -m pytest -q` ve kalite komutunu çalıştırın. Sonrasında container sağlığını, `source-grounded-v4` sürümünü, bir yeni taslakta dört düzenleme düğmesini ve `/haber_kalite` komutunu doğrulayın. Testte gerçek haber/model veya Telegram gönderimi yapılırsa bunu çevrimdışı test sonuçlarından ayrı raporlayın. Diğer Hermes/Her An Borsa servislerine dokunmayın.
