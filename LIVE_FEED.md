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

Tweet biçimi: Doğrulanmış başlık/olgulara göre 2–3 konu etiketi eklenir. Uygun yüksek etkili haberlerde 🚨, diğer uygun haberlerde 📢 yalnız başlığın önünde kullanılır; metin sonuna emoji eklenmez ve ölüm haberlerinde emoji kullanılmaz. Kullanıcının istediği taslak en fazla 380 karakterdir. Modelin kanıt denetimi öncesi gövdesi değişmez; süslemeyi uygulama sonradan ekler. 219 test geçti.


## İçerik ve teslimat sağlamlaştırması — 6 Ekim 2026

Kaynak URL'si, canonical URL, başlık, seçilen ana metin ve iş dosyasının özeti birbirine bağlanır. Birden çok haber bloğunda doğru haber seçilemiyorsa metin modele verilmez. Menü, öneri, etiket, dipnot ve fotoğraf kredileri metinden ayrılır. Olgu cümlesindeki koşul, iddia, yalanlama ve atıf bölümleri kırpılamaz. Yeni haber taslakları başlık, kaynak, emoji ve etiketler dahil en fazla 380 karakterdir; eski kayıtlar ve sosyal gönderi sözleşmesi 550 sınırını korur.

Tek bir haberin biçim/kanıt hatası bütün model akışını durdurmaz. Biçim hataları sınırlı sayıda düzeltilir; kaynaktaki gerçek belirsizlik uydurma metinle kapatılmaz. Süresi geçen iş rezervasyonları serbest bırakılır; sonucu belirsiz çağrı otomatik tekrarlanmaz.

Fotoğrafın dosya özeti gönderim öncesinde yeniden doğrulanır. Telegram açıklaması fotoğrafın üstünde gösterilir. Fotoğraf kesin olarak reddedilirse veya dosya bütünlüğü bozuksa aynı teslimat sade taslak metnine döner; teknik çıktı gönderilmez. Teslim sonucu belirsiz ağ kesintisinde çift mesaj riski nedeniyle otomatik ikinci gönderim yapılmaz.

6 Ekim temel sürümünde 219 otomatik test geçti. 28 gerçek URL örneğinin 25'inde metin çıkarma ve Collector→AI iş girdisi bağlantısı doğrulandı; bir galeri belirsiz gövde nedeniyle durduruldu, iki Investing sayfası HTTP 403 verdi. Üç gerçek model denemesinde 205, 301 ve 294 karakterlik taslaklar doğrulandı; bir biçim hatası ikinci çağrıda düzeldi. Kayıt: `reports/HARDENING_AUDIT.json`.

## Gerçek fotoğraf teslimi — 7 Ekim 2026

Kaynak görseli yalnız aynı haberin `og:image`, `twitter:image`, haberle URL bağı doğrulanmış JSON-LD veya seçilmiş haber içindeki görsel alanından alınır. Menü, reklam, logo ve diğer haber görselleri kullanılmaz. Hostlar önceden belirlenir; sayfa yeni ağ yetkisi veremez. Public DNS/HTTPS/redirect, 10 MB indirme sınırı, MIME/magic, decode/piksel ve boyut kontrolleri uygulanır. Fotoğraf kaynak ana metin digest'iyle bağlanır. Dosya JPEG olarak normalize edilir; Telegram'a multipart `sendPhoto` ile yüklenir ve tweet açıklaması üstte gösterilir. Görsel bulunamazsa bağlantı önizlemesi yerine yalnız metin gelir.

Özel sohbet önizlemesinin kaydı yeniden yayınlama izninden ayrıdır: `private_source_preview`/`unknown`. Bu dosya yeniden kullanım hakkı doğrulanmış medya diye export edilmez. Hakları doğrulanmış arşiv yolu korunur. Görsel indirme denemesi üç aday ve yaklaşık 20 saniye ile sınırlıdır; erişim engeli aşılmaz.

237 otomatik test geçti; yanlış haber/görsel eşleşmesi, yabancı CDN, bozuk dosya, WEBP dönüşümü, fotoğraflı tek mesaj, özel sohbet sınırı, multipart upload ve yayınlama paketinde hak ayrımı doğrulandı. Canlı kaynak örnekleri ve mevcut taslağın aynı mesajdaki fotoğraf düzeltmesi: `reports/PHOTO_DELIVERY_AUDIT.json`.
