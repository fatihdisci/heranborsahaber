# Günlük devre kesici — onaylı 40 hisse seçkisi

Bu kural yalnız `/devrekesici` günlük raporudur. Kullanıcının yeni açık onayı, bu raporda önceki tüm-satırları-göster zorunluluğunu değiştirir. Diğer devre kesici bildirim grupları, geri alımın ilk-10 tweet seçimi ve tüm satırlı görselleri, AKD/takas ürünleri değişmez.

## Gösterim ve arşiv

Bildirimler önce İstanbul günü/komut zamanı, kimlik tekilleştirmesi ve düzeltme ilişkileriyle sayılır; gösterim limiti bu denetimlerin sonrasındadır. Bir hissenin ayrı olayları sayılır, aynı bildirim kimliği tekrar sayılmaz. Aynı hisse görselde tek satır, tekrar sayısı ve doğrulanmış endeks grubuyla yer alır.

Öncelik BIST30 → BIST100 (BIST30 hariç) → diğer. **Grup içinde tekrar sayısı azalan, eşitlikte ASCII hisse kodu artan** sıralama kullanılır. BIST50 ayrı katman değildir. En çok 40 benzersiz hisse seçilir. Açık ilk-N isteği 40'tan az olabilir; `all` bu ürünün onaylı 40 üst sınırını kaldırmaz. Tweet ve bütün görseller aynı seçilmiş kümeyi kullanır.

Tam `events` listesi kimlik/hisse/zamanlarıyla; `circuit.all_rows` tam hisse toplamlarıyla taslakta korunur. Seçim sürümü, kural kimliği, gerçek toplamlar, gösterilen kodlar ve gösterilmeyen sayı saklanır. Doğrulanmış BIST30/BIST100 listesinin birebir anlık görüntüsü, kaynak URL'si ve kontrol zamanı bu sürüme bağlanır. Kaynak KAP kayıtları silinmez. Geçmiş taslaklar dönüştürülmez veya tekrar gönderilmez.

Üyelik için mevcut resmî KAP endeks listesi kullanılır: 30/100 benzersiz geçerli kod, alt-küme ilişkisi, resmî kaynak URL'si, en fazla 36 saatlik kontrol ve en fazla beş dakikalık saat farkı doğrulanır. Eksik, stale, bozuk veya güvenilmeyen üyelikte dolu rapor `circuit_report_indices_unavailable` ile durur; öncelik veya insan onayı uydurulmaz. Boş gün için hayalî hisse/endeks üretilmez.

Gösterilmeyen hisse varsa kısa ve zorunlu dipnot hem tweette hem her PNG'de bulunur: `400 hisse; 360 gösterilmedi.` İsteğe bağlı alt bilgiyi gizlemek bu esaslı kapsam bilgisini gizlemez. Kaynak adı, saat ve ek dekoratif dipnot yoktur. Kapsam gecikmesi gibi ayrıntılar editör kanıtında kalır.

## Gerçek örnek ve tweet kapasitesi

23 Ekim 23:08:48 TRT komutu için kullanılan veri, mevcut kamuya açık KAP önbelleğinin aynı zaman sınırıyla **yeniden kurulmuş** halidir; orijinal hata-anı snapshot'ı veya üretim teslimat kaydı değildir. Fixture'ın köken etiketi korunur. 730 adaydan 475 farklı `DUY/DUY` / `Pay Bazında Devre Kesici Bildirimi`, tamamı aynı İstanbul günü ve komut saatinden önce; 400 farklı hisse. Bu sayılar limit uygulanmadan doğrulanır.

Yeni sıralama 23 BIST30 ve 17 diğer BIST100 hissesini seçer. Tam toplam 400, gösterilmeyen 360; 475 olay ve 400 hisse toplamı arşivde kalır. Başlık + 40 kod + dipnot iki biçimde gerçek `twitter-text` ağırlığıyla hesaplanır:

- `#KOD` ile 319/280: sığmaz.
- Aynı 40 kod hashtagsiz 279/280: geçerli. Ek genel hashtag veya emoji eklenmez. Bu özel hashtagsiz izin diğer ürünlere yayılmaz.
- Önce # biçimi denenir; sığan küçük listede # korunur. Hashtagsiz de sığmayan örnekte kod düşürülmez: gerçek uzunluk ve aynı öncelik sırasında sığabilecek kod sayısı açıklanır. Sentetik 1000 hisselik testte 40 kod 283 karakterdir; 39 kod ancak açık ilk-39 seçimiyle üretilir. Otomatik thread/uzun-post varsayımı yoktur.

40 satır mevcut 1080×1350 şablonda **14/13/13 satırlı üç PNG** olur. Yazı boyutları değişmez; tablo 30/28 px, zorunlu not 26 px, sayfa numarası 24 px. Üç gerçek PNG görsel olarak incelendi; taşma/kırpılma/çakışma görülmedi. Önizleme `reports/circuit-selection-preview/` altında, tekrar üretim `node --import tsx scripts/preview_circuit_selection.ts`.

## Doğrulama ve geçiş sınırı

- Node 22: TypeScript kontrolü; tam 392 test; dry-run build.
- Gerçek yeniden kurulmuş 400-hisse verisiyle seçim/tweet/kart küme eşitliği; tekrar sayıları; eski/yeni gün ve yinelenen ID; BIST50'nin öncelik yaratmaması; eşitlik sırası; boş/küçük veri; eksik/stale/bozuk/future üyelik; zorunlu notun korunması testleri.
- İzole DB ve gerçek PNG renderer ile komut → üç medya dosyası → tek sahte Telegram albümü → teslimat tekrar koruması. Açık Paylaş isteğinden önce sahte X taşıyıcısı bile çağrılmaz; açık istekte üç upload ve aynı 279 karakterli metinle tek sahte POST. Gerçek Telegram/X/model çağrısı yoktur.
- Mevcut Python venv'i 67 test; ayrı macOS Vision OCR 1 ve geri alım OCR 3 kontrolü (bunlar toplam 67 içindedir).
- ZIP temiz staging: 21 örnek grubu, 26 PNG, 105 dosya manifesti, transitif kaynak kapanımı, güncel runtime eşitliği; bağımsız CLI ile eski dört-sayfa ve yeni üç-sayfa örnekleri yeniden üretildi. Paket aynı `selectCircuitReport`/`circuitOmissionNote` kodunu taşır. Kaynaktan güncel endeks çektiğini iddia etmez.

ZIP SHA256: `7916100962f698d8482645e053ebda8636c5454bff5de2c52b1c488b7548aec5`.

Bu, kod ve yerel test raporudur; CI ve canlı sürüm ayrıca operasyon makbuzuyla doğrulanır. SQL şeması değişmez. Dağıtım yalnız haber servisini gerektirir; KAP/panel/DNS/ağ ayarları, kullanıcı oyları, model/oturum, shadow filtre ve kapalı seçki korunur. Tutarlı yerel DB/yapılandırma/uygulama/teslimat yedeği alınır. Geri dönüşte güncel DB korunur; eski geliştirme DB'si kopyalanmaz, belirsiz teslimler tekrar oynatılmaz. Önceki e313484 uygulaması aynı çoklu medya şemasını okur; daha eski, çoklu medyayı bilmeyen bir sürüme dönüş gerekiyorsa mevcut `hold_multi_cards.py` koruması ve bilinen kontrol düğmelerini kapatma adımı önce uygulanmalıdır. Bu tur eski başarısız komut veya eski rapor yeniden gönderilmez. Gerçek yeni Telegram albümü ve gerçek açık-onaylı X yayını bu testten ayrı, henüz doğrulanmamış olaylardır.
