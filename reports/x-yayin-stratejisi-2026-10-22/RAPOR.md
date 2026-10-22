# ENDEKS HABER — X yayın sıklığı ve dağıtım raporu

Araştırma tarihi: **22 Ekim 2026**. Hesap: **@endeks_haber**. Saatler: **Europe/Istanbul**.

## Karar

ENDEKS HABER için başlangıç denemesi: normal işlem gününde **8–12 özgün ana paylaşım**, rutin içerikler arasında **45–75 dakika**; yoğun haber gününde **12–16**, olağanüstü gündemde **20’ye kadar**. Bunlar algoritmanın ilan ettiği eşikler değil, hesabın içerik yüküne göre önerdiğim editoryal test aralıklarıdır. 20 bir hedef değil, kullanıcının seçtiği bütçe üst sınırıdır. Sırf sayıyı doldurmak için paylaşım yapılmamalı.

En büyük fırsat daha fazla içerik üretmek değil, dakikalar içinde arka arkaya yayımlanan benzer içerikleri seçmek ve gruplamaktır. Son dakika haberini sırf önceki tweet yayılsın diye bekletmeyin. Rutin geri alımların tamamını tek tek X’e taşımak yerine genel geri alım tablosunu ana içerik yapın; önemli program değişikliklerini ayrıca yayımlayın.

Bu rapor araştırma ve öneridir; yayıncı ayarları, otomatik gönderim, canlı kuyruk veya bütçe limiti değiştirilmedi.

## 1. Hesabın mevcut durumu: ölçtüğüm şeyler

Herkese açık profil ve RSS, Nitter üzerinden okundu. Hesap adı ve gönderi bağlantıları eşleştirildi; sabitlenmiş gönderi ikinci kez sayılmadı. Gönderi kimliklerinden zaman çıkarılıp İstanbul saatine çevrildi. Eski tarihli veya farklı hesaplara ait içerikler güncel analize katılmadı. Nitter önbellekli ve eksik olabilir; aşağıdaki sayı **günün kesin toplamı değil, doğrulanabilen alt sınırdır**.

| Ölçüm | Gözlem |
|---|---:|
| 22 Ekim, 11:26:39–18:49:17 arasında görülen özgün gönderi | 45 |
| Bu 45 gönderinin 44 aralığındaki ortanca | 6 dakika 47 saniye |
| En kısa aralık | 16,72 saniye |
| 1 dakikadan kısa aralık | 6/44 |
| 3 dakikadan kısa aralık | 14/44 |
| 18:00–18:49 arasında gönderi | 14 |
| Son 20 gönderi: 17:00:56–18:49:17 | 1 saat 48 dakika 21 saniye |
| Son 20 gönderide ortanca aralık | 2 dakika 31 saniye |
| Son 20 gönderide 3 dakikadan kısa aralık | 10/19 |
| Güncel 45 gönderide devre kesici içerikleri | 10 |
| Güncel 45 gönderide geri alım ifadesi içeren içerikler | 11 |

Veri eki: [hesap-ornegi.json](hesap-ornegi.json). Profil anlık görüntüsünde yaklaşık 6.099 takipçi görünüyordu; bu sayı erişim veya aktif takipçi sayısı değildir.

Örnekler:

- [17:29:04 piyasa katkıları](https://x.com/endeks_haber/status/2113276457195823552) ardından [17:29:35 devre kesici](https://x.com/endeks_haber/status/2113276583817756859): **31 saniye**.
- [18:31:23 TKNKA](https://x.com/endeks_haber/status/2113292137785676202) ardından [18:31:46 KPEKS](https://x.com/endeks_haber/status/2113292235626181087): **23 saniye**.
- 18:06–18:33 arasında çok sayıda ayrı geri alım paylaşımı var. Farklı şirketler olduğu için bunlar birebir kopya değil; fakat okuyucunun karşısına benzer haber ihtiyacını karşılayan bir seri çıkıyor.
- Piyasa katkıları paylaşımında 14 hashtag bulunuyor. Çok sayıda ilgili şirket kodu otomatik spam kanıtı değildir; ancak okunabilirlik ve mesaj odağı bakımından azaltılabilir.

Yerel `x_posts` tablosunda iki başarılı API yayını vardı. Bu, hesabın yalnızca iki paylaşım yaptığı anlamına gelmiyor: web/telefon üzerinden yayımlananlar yerel API sayacında yok. Dolayısıyla **20 API gönderisi limiti toplam hesap sıklığını kontrol etmiyor**. Günlük plan manuel gönderileri de saymalı.

Özel X Analytics, takipçi aktif saatleri, takipçi kazanımı, sabit yaşta gösterim serileri ve takipten çıkış verileri elde edilmedi. Bu nedenle “sık attığın için erişimin yüzde X düşmüş” sonucu çıkarılamaz. İçerik takvimi ölçüldü; nedensel performans testi yapılmadı.

## 2. Güncel algoritma kodu ne söylüyor?

Eski [twitter/the-algorithm](https://github.com/twitter/the-algorithm) deposu tarihsel bağlam için incelendi. Güncel analizde **xai-org/x-algorithm** esas alındı: **989fb91254d461bf4b9df53fb12d5c9a61c2b354**, commit zamanı **22 Ekim 2026 06:49:38 UTC**. Daha eski blogların katsayıları bugüne taşınmadı.

### Aynı yazarın gönderileri birbiriyle yarışabiliyor

Güncel kodda mekanizma birden fazla aşamada bulunuyor. `home-mixer/scorers/value_model.rs` içinde yazar çeşitliliği kapalı görünse de bu tek dosyaya bakıp “mekanizma yok” demek yanlış olur: sonraki **VMRanker** aşamasında `EnableAuthorDiversity=true`, decay `0.5`, floor `0.25` varsayılanları var. [VMRanker parametreleri](https://github.com/xai-org/x-algorithm/blob/989fb91254d461bf4b9df53fb12d5c9a61c2b354/vm-ranker/params.rs), [aşamanın ağırlık bağlantısı](https://github.com/xai-org/x-algorithm/blob/989fb91254d461bf4b9df53fb12d5c9a61c2b354/vm-ranker/scoring/value_model.rs).

`author_pool_counts`, adayları puan sırasına koyup aynı yazardan önce gelen adayları sayıyor. `diversity_multiplier` formülü `0.75 × 0.5^k + 0.25`; ilk birkaç çarpan 1, 0.625, 0.4375 ve 0.34375. Bu **aynı değerlendirmedeki aday puanına** uygulanan bileşendir; gösterim kaybı yüzdesi değildir. Günün ikinci tweet’i veya kronolojik olarak yeni tweet otomatik olarak ikinci sıraya konmaz. [Hesaplama kodu](https://github.com/xai-org/x-algorithm/blob/989fb91254d461bf4b9df53fb12d5c9a61c2b354/xai-value-model/scoring.rs).

Pratik çıkarım: birbirine çok yakın, benzer içeriklerin aynı okuyucunun dikkatini ve aday havuzunu paylaşması mümkündür. Fakat buradan “iki tweet arasında tam 30/60/120 dakika olmalı” sonucu çıkmaz. Kodda bu formül bir yayın aralığı zamanlayıcısı değildir.

### Kişiye göre tahmin, kalite ve dikkat

Sıralama, etkileşim ve okuma/izleme davranışı tahminlerini birleştiriyor. Ağırlıklar ham beğeni sayısına uygulanmıyor; “bir şikâyet 468 beğeniyi siler” gibi hesaplar yanlış. Okunabilir, faydalı tablo üretmek mantıklı; metni yapay biçimde uzatmanın otomatik kazancı yok. Kamuya açık kod tüm üretim detaylarını ve her deney grubunu göstermiyor. [Resmî README: puanlama, deneyler ve kapsam](https://github.com/xai-org/x-algorithm/blob/989fb91254d461bf4b9df53fb12d5c9a61c2b354/README.md).

For You, Following, arama ve bildirimler aynı dağıtım yüzeyi değildir. Tek sıralama bileşeni bütün erişimi açıklamaz. Takip/ilgi/etkileşim geçmişi de kişiselleştirmeyi etkiler. [X’in öneri açıklaması](https://help.x.com/en/rules-and-policies/recommendations).

## 3. Araştırmalar, deneyler ve forumlar

| Kaynak | Bulgusu | Bu hesaba uygulanırken sınırı |
|---|---|---|
| [Buffer 2026 genel raporu](https://buffer.com/resources/state-of-social-media-engagement-2026/) | Çok platformlu 52 milyonun üzerinde gönderilik çalışma; sıklık ile toplam sonuç ve gönderi başına sonuç farklılaşabiliyor | Gözlemsel, Buffer kullanıcıları; BIST haber hesabına özgü kontrollü deney değil |
| [Buffer sıklık rehberi](https://buffer.com/resources/social-media-frequency-guide/) | Özet tabloda X için 3–4 paylaşım/gün öneriyor | Editoryal rehber; algoritmanın teknik optimumu değil. Haber hesabına aynen uygulamak gerekmiyor |
| [Buffer X saat analizi](https://buffer.com/resources/best-time-to-post-on-twitter-x/) | Metinde 8,7 milyon gönderi; hafta içi sabahları, özellikle 09–11 öne çıkıyor | Sayfa başlık/metaverisinde örneklem sunumu tutarsız olabiliyor; Türkiye finans alt örneklemi yok |
| [Sprout Social 2026](https://sproutsocial.com/insights/best-times-to-post-on-twitter/) | Salı–perşembe 12–18; 27 Kasım 2025–27 Şubat 2026 verisi | Yaklaşık 2 milyar etkileşim/307 bin profil tüm incelenen platformların toplamı; X-only örneklem değil |
| [The Half-Life of a Tweet, 2023](https://arxiv.org/abs/2302.09654) | Ön analizde ortanca gösterim yarı ömrü yaklaşık 80 dakika | Eski Twitter dönemi, bugünkü hesaba garanti değil; 80 dakika sonra dağıtım biter demiyor |
| [Reddit: sık paylaşım erişimi düşürüyor mu?](https://www.reddit.com/r/SocialMediaMarketing/comments/1qp2q73/posting_more_on_twitter_i_mean_x_will_limit_your/) | Bazı kullanıcılar daha az ama daha özenli yayınla daha iyi etkileşim bildirmiş | Ham veri/kontrol grubu yok; deneyim ve yorum |
| [Reddit: kendi verim genel saat tavsiyesinden farklı](https://www.reddit.com/r/socialmedia/comments/1swc6vm/i_analyzed_my_actual_tweet_engagement_data_to/) | Hesaba özel saatleri, tweet yaşı hesaba katılarak inceleme öneriliyor | Kullanıcı beyanı; bağımsız tekrar üretim yok |
| [Reddit: daha fazla paylaşmak sonuçları kötüleştirdi mi?](https://www.reddit.com/r/TwitterMarketing/comments/1wshe73/has_posting_more_ever_made_your_results_worse/) | Sıklık/kalite sorusu tartışılıyor | Erişilen sayfa kontrollü deney sonucu sunmuyor |

Buffer ile Sprout’un saat önerilerinin farklı olması hata olmak zorunda değil: örneklem, sektör, dönem ve başarı ölçütü farklı. Bu nedenle “dünyada en iyi saat salı 09:00, sen de yalnız o saatte paylaş” önerisi yapmıyorum. Finans haberinin olay zamanı, küresel pazarlama saatlerinden daha anlamlı olabilir.

Forumdaki “üçüncü hashtag shadowban yapar”, “ilk 30 dakikada cevap gelmezse tweet ölür” veya “yeni tweet eskisini tamamen durdurur” türü kesin kurallar için doğrulanmış kanıt bulunmadı. Koddan ve çalışmalardan, kontrollü X yayın sıklığı deneyinin yerini tutacak bir kesin optimum çıkarılamıyor.

20 Ekim tarihli yeni dikkat/okuma modelleri haberleri de tarandı. Doğrudan dağıtım etkisini ölçen bağımsız deney elde edilmediği için haber başlıklarındaki büyüme iddiaları bu planın sayısal dayanağı yapılmadı.

## 4. Soruların doğrudan cevapları

**Çok sık paylaşmak iyi mi?** Daha çok görünme fırsatı yaratabilir; fakat her gönderinin ortalama performansını artırmak zorunda değildir. Günlük toplam erişim ile gönderi başına erişimi ayrı ölçmeliyiz. Senin hesabında 45 paylaşımın kalıcı optimum olduğu gösterilmiş değil; özellikle kapanıştaki seri geri alımlar azaltılabilecek yoğunluk yaratıyor.

**Yeni paylaşım eskisinin önüne geçer mi?** Bazı okuyucularda rekabet edebilir. Öncekinin dağıtımını herkese kapatan evrensel bir kural bulunmadı. “İyi gidiyor diye önemli haberi iki saat bekletmek” finans haberciliğinde yanlış olabilir.

**Bir tweet’in yayılması ne kadar sürer?** Sabit süre yok. İlk dakikalar ve saatler ölçülmeli, 24 ve 48 saatte yeniden bakılmalı. 2023 çalışmasının 80 dakika yarı ömrü son kullanma tarihi değildir. Bugünkü For You akışındaki yaş filtresi de bir erişim garantisi veya bütün X için ömür sınırı olarak okunmamalı.

**Spam sayılır mı?** Sıklık tek başına bir teşhis değil. X’in politikası toplu/tekrarlı, alakasız veya istenmeyen içerik ve manipülasyonu hedefliyor; aşırı ve ilgisiz etiket kullanımı da belirtiliyor. “Günde 21 paylaşım spamdır” diye bir editoryal eşik yayımlanmıyor. Platform teknik limitleri ile tavsiye edilen yayın sayısı ayrı konular. [X özgünlük politikası](https://help.x.com/en/rules-and-policies/authenticity).

**Minimum kaç?** Algoritmik minimum bilinmiyor. Haber değeri varsa sakin işlem gününde 4–6 kaliteli ana gönderi yeterli bir başlangıç; hafta sonu 1–3 bilgi/haftalık özet. Haber yoksa boşluğu doldurmak için zayıf içerik üretmeyin. Düzenli görünürlük ayrıca gerçek sorulara cevap vermekle korunabilir.

**Maksimum kaç?** İlk testte rutin gün 8–12, yoğun gün 12–16; gerçek olağanüstü gündem için 20’ye kadar. Bunlar garanti güvenli/spam sınırları değil. Manuel gönderiler dahil toplamı takip edin; mevcut API limiti aynen korunmalı.

## 5. ENDEKS HABER yayın planı

Aşağıdaki saatler BIST odaklı editoryal öneridir; ölçülmüş takipçi aktif saatleri değildir. Bütün aralıklarda yayın zorunlu değil; toplam günlük hedef geçerli.

| İstanbul saati | İçerik | Yaklaşık pay |
|---|---|---:|
| 08:45–09:30 | Gece küresel gelişmeler, güne hazırlık | 1 |
| 10:05–11:15 | Açılış görünümü / önemli şirket haberi | 1–2 |
| 12:00–13:15 | Gün ortası kurum/AKD veya önemli KAP | 1–2 |
| 14:00–16:00 | Yeni önemli gelişmeler; karar varsa olay anında | 1–2 |
| 17:15–18:20 | Kapanışa doğru ve kapanış özeti | 1–2 |
| 19:00–20:30 | Bilanço seçkisi, toplu geri alım ve gün raporu | 2–3 |
| 21:00 civarı | Yalnız önemli geç haber veya ertesi gün ajandası | Gerektiğinde |

Rutin paylaşımlar için **45–75 dakika** başlangıç hedefi. Bekleyebilen iki güçlü tablo arasında **60–90 dakika** denenebilir. Haber yoğunluğunda **20–30 dakika** aralık kullanılabilir. Son dakika TCMB/SPK/önemli şirket açıklaması doğrulanınca yayımlanır; bu aralıkların istisnasıdır. Önceki ana içerik henüz birkaç dakikalıksa, önemsiz ikinci haberi bekletmek veya özete almak daha mantıklı.

### İçerik türlerine göre karar

- **Geri alım:** Gün içinde gelenlerin tamamı sistemde/Telegram’da kalabilir. X’te genel tablo + gerçekten önemli 1–2 ayrı gelişme tercih edin. Yeni 5 milyar TL program kararı ile rutin 50 bin pay işlemini aynı önemde sunmayın. Veri tarihi ve kapsanan saat yazılı olsun.
- **Devre kesici:** Üç dakikalık toplama iç sistem için yararlı; her grubun X’e gitmesi zorunlu olmasın. Piyasa çapında dalga veya önemli hisseler anlık, diğerleri seçilmiş toplu güncelleme/gün raporu olabilir. Eski devre kesiciyi sırf sıra bekledi diye yeni uygulanmış gibi paylaşmayın.
- **Bilanço:** Büyük sürpriz, önemli dönemsel değişim veya takip edilen şirket için ayrı içerik. Diğerlerini birkaç şirketlik seçkide gruplayın; dönem, birim ve konsolide/konsolide olmayan ayrımını koruyun.
- **AKD/kurum:** Gün ortası ve gün sonu aynı veriyi küçük değişikliklerle çok kez yinelemek yerine net iki ayrı zaman kesiti. İşlemler “kurum üzerinden” diye yazılmalı.
- **Genel haber:** Yatırımcıya yeni bilgi katmayan tekrarları X’e taşımayın. Kaynağa erişim ve kanıt kaydı sistemde kalsın.

Her ana paylaşımda tek net haber, mümkünse tarih/dönem/birim içeren okunaklı görsel ve faydalı ilk cümle kullanın. Çok büyük tabloların tamamı indirilebilir PNG’de bulunabilir; telefonda okunacak özet ayrı önem taşır. Okuma süresini artırmak için yazıları küçültmek veya gereksiz metin eklemek önerilmez.

Tek şirket haberinde ilgili hisse etiketi yeterince görünür olsun. Çok şirketli tabloda ilk beş alış/ilk beş satış gibi sınıflandırılmış kodlar korunabilir; bunların yanına tekrar uzun genel etiket listesi eklemeyin. Konuyla ilgisiz #halkaarz gibi etiketler kullanılmasın. Etiket sayısını artırmanın dağıtımı otomatik artırdığı gösterilmiş değil. Mevcut etiket politikası bu raporla kendiliğinden değiştirilmedi.

## 6. En iyi aralığı gerçekten bulacak dört haftalık test

**Amaç:** 45 gönderilik kısa süreli yoğunluğa dönmeden, toplam nitelikli erişimi ve takipçi kazanımını koruyan/yükselten sıklığı bulmak.

1. **İlk iki hafta:** Rutin günleri 8 ve 12 ana gönderilik iki plana dengeli dağıtın. Aynı hafta gününün sonraki haftada karşı planı görmesini sağlayın. Ana zaman pencereleri ve içerik kalitesi mümkün olduğunca benzer kalsın. Acil haberler iki planda da bekletilmesin; ayrı etiketlensin.
2. **Sonraki iki hafta:** Daha iyi görünen günlük sayıyı sabitleyin. Yalnız bekleyebilen içeriklerde yaklaşık 30–45 ve 60–75 dakika aralığı karşılaştırın. Günlük sayı ile saat aralığını aynı anda kontrolsüz değiştirmeyin. Her zaman penceresi için yeterli tekrar yoksa testi uzatın.
3. **Her gönderide kaydedin:** URL, yayın zamanı, tür, acil/rutin, önceki gönderiye dakika, manuel/API, hisse sayısı, metin/görsel türü. 15 dakika, 1 saat, 3 saat, 24 saat ve 48 saatte ulaşılabilen gösterim ve etkileşimleri ölçün. Eksik metrikleri sıfır saymayın.
4. **Başarı:** Günlük toplam gösterim, günlük net takipçi kazanımı, 24 saatlik gönderi başına ortanca gösterim; mümkünse paylaşım/yer imi/profil ziyareti ve oranları. Günlük gösterim toplamı tekil kişi erişimi değildir. Her kategori ayrı değerlendirilsin.
5. **Karar:** Daha az gönderiyle günlük toplam sonuç korunuyor ve gönderi başına kalite yükseliyorsa düşük sıklığı seçin. Daha yüksek sıklık günlük sonucu açıkça artırıyor, kalite ve olumsuz geri bildirim bozulmuyorsa artırın. Az sayıdaki viral içeriği bütün planın başarısı sanmayın; ortanca ve toplamı birlikte inceleyin.

TCMB karar günü, sert piyasa hareketi ve yoğun bilanço günü normal günlerle doğrudan eş tutulmamalı. Dört hafta yön gösterir; kesin nedensellik veya her dönem geçerli optimum sağlamaz. 45 gönderilik örnek tek bir yoğun günün kesitidir.

Bu çalışma sırasında gerçek bir A/B yayın deneyi, otomatik analitik toplama veya yeni zamanlayıcı kurulmadı. Yukarıdaki test uygulanacak plan olarak sunuluyor.

## 7. Kapsam ve tekrar üretilebilirlik

- Araştırma birincil algoritma kodu/politikalar, güncel ticari araştırmalar, akademik çalışma ve örnek Reddit tartışmalarını kapsar; internetteki bütün iddia ve deneylerin eksiksiz tarandığı iddia edilmez.
- Agent-reach becerisi okundu; CLI kurulu olmadığı için web aracı, kamuya açık GitHub ve mevcut Nitter yolu kullanıldı. Ücretli X okuma API çağrısı yapılmadı.
- İncelenen kod commit’i sabitlendi; blogların eski katsayıları güncel diye aktarılmadı. GitHub kodunun bazı üretim ayarları ve açıklanmayan kuralları kapsamadığı dikkate alındı.
- Herkese açık hesap verisinde 22 Ekim dışındaki içerikler ve yinelenen kimlikler çıkarıldı. Profil geçmişinin tamamına ulaşıldığı varsayılmadı.
- Sayımlar `hesap-ornegi.json` içindeki gönderilerden tekrar hesaplanabilir. Yalnız kamuya açık gönderi kimlikleri, başlıkları, saatleri ve etiketleri kaydedildi; token, Telegram kimliği veya özel mesaj yok.
- Canlı sistem değiştirilmedi. Rapor için uygulama testleri gerekmiyor; veri sayımı, bağlantı biçimleri ve Git diff kontrol edildi.

## 8. Uygulama takibi — 22 Ekim 2026

Araştırmadan sonra eklenenler:

- Manuel ✅ işaretleri ve başarılı API yayınlarını tekilleştiren ortak sayaç; İstanbul gün sınırı, son yayın zamanı, geri alma ve saat düzeltme.
- Telegram ve Mini App’te aralık/günlük toplam önerisi. Rutin 45–75 dakika, büyük tablolar için 60–90 dakika; 12/16/20 toplamda seçicilik uyarısı. Hafta sonu daha hafif plan. Bunlar engelleyici algoritma kuralları değildir; son dakika bekletilmez.
- `/yayinplani`: yayın pencereleri, içerik seçimi ve dört haftalık karşılaştırma planı.
- `/yayinraporu`: son 28 günün kayıtlı yayınlarını CSV olarak verir. Yayın zamanı, yöntem, bilinen API tweet bağlantısı, önceki yayına dakika, mevcut kart başlığı/kategorisi/şablonu ve doğrulanmış kodlar bulunur. Acil/rutin, deney grubu ve 15 dk/1/3/24/48 saat gösterim alanları boş bırakılır. Bilinmeyen metrik sıfır değildir. Başlık ve türler mevcut taslağa aittir; geçmiş X içeriğinin değişmez kopyası sayılmaz.
- Mevcut 20 API/gün limiti korunur. Manuel sayım bütçeyi tüketmez; rapordaki editoryal toplam önerisiyle API limiti farklıdır.

Hesap sahibinin yapacakları:

1. Elle yayımladığını ✅ ile kaydet; geç işaretliyorsan gerçek yayın saatini 🕒 ile düzelt. Önceki kayıt dışı paylaşımlar otomatik bulunmuş sayılmaz.
2. Normal gün 8–12 güçlü içerikle dene; sayı doldurma. Rutin geri alımlarda genel tabloyu, AKD’de gün ortası/gün sonu kesitlerini, devre kesicide önemli dalgaları seç. Acil haberi takvim uğruna bekletme.
3. İlk iki haftada 8/12 planlarını dengeli karşılaştır; sonraki iki haftada günlük sayıyı sabit tutarak aralığı karşılaştır. CSV’de acil/rutin ve deney grubunu belirt.
4. X Analytics üzerinden aynı yaştaki gönderim sonuçlarını ve günlük takipçi değişimini kaydet. CSV’de elle paylaşılan gönderi URL’lerini ekle. Gösterim toplamı tekil erişim değildir.

Açık kalan veri ihtiyacı: özel X Analytics erişimi/çıktısı olmadan gerçek performans, takipçi artışı veya hesaba özel en iyi saat hesaplanamaz. Ücretli okuma, otomatik metrik taraması, yeni hatırlatma görevi veya otomatik paylaşım başlatılmadı. Önce ölçüm biriktirilecek; optimum iddiası yapılmayacak.
