# Her An Borsa — bağımsız habnews haber masası

Güncel model: **gpt-6-luna**, düşünme açık, **reasoning effort high**. Otomatik düşük effort/model seçimi yok.

Katalogda 17 kaynak tanımlı; 6 Ekim 2026'daki canlı ayarda 16'sı etkin: 12 haber/resmî akış ve 4 X hesabı. **Investing Türkiye kapalıdır.** Kaynak adayları ve doğrulama sınırları: [SOURCE_AUDIT.txt](reports/SOURCE_AUDIT.txt); önceki erişim ölçümleri: [public-source-expansion.json](reports/public-source-expansion.json).

Tweet oluştur yalnız haber başlığı ve ana metninden en fazla 380 karakterlik tek taslak üretir. 🚨/📢 başlığın önünde, 2–3 konu etiketi metinde yer alır. 7 Ekim 2026 düzeltmesiyle haberin kendi ana görseli dosya olarak yüklenir; tweet aynı Telegram fotoğrafının açıklamasındadır. Bu özel kaynak önizlemesi yeniden yayınlama lisansı sayılmaz. Görsel yoksa sade tweet metni gönderilir. Ayrıntılar: [LIVE_FEED.md](LIVE_FEED.md).

Ayrı Python uygulaması, SQLite WAL, kalıcı aşama kuyruğu, Hermes dosya iş sözleşmesi, özel Telegram inceleme/onay servisi ve Linux/container kurulum paketi. X veya başka yayın servisine gönderim yolu yoktur. Onay tam taslak/sürüm/görsel hash'ini kaydeder; yayın yapmaz.

**Haber filtresi:** Başlık/özet içindeki Türkiye, yerli kurum/piyasa/şirket sinyallerinden biri yeterlidir; genel Fed/altın/petrol haberi tek başına geçmez. SPK haberleri alınır; rutin KAP geri alım/pay işlemleri ve açık yatırım tanıtımları elenir. Dört X hesabı aynı yerel alaka filtresinden geçer.

**Kurulum durumu (6 Ekim 2026):** Ayrı `habnews` Colima/Linux kurulumu altı container kullanır; son sağlık kontrolünde collector sağlıklı, model hazır, Investing devre dışı ve 16 etkin kaynak görünüyordu. Bu kurulum mevcut Hermes ve Her An Borsa servislerinden ayrıdır. Güncel işletim bilgileri: [MACOS.md](MACOS.md).

- Dağıtım paketindeki `sources.yaml` güvenli varsayılan olarak bütün kaynakları kapalı tutar. Kurulu instance kendi ayrı kaynak yapılandırmasını kullanır.
- Foreks ve Bloomberg HT 60 saniyede; Habertürk, Sözcü, Dünya ve Ekonomim 120 saniyede; diğer etkin RSS/resmî ve X akışları 180 saniyede taranır. Investing'in geçmişte gözlenen HTTP 403 tam metin erişimi nedeniyle kaynak devre dışı bırakıldı.
- Hermes: upstream `dd0e4ab81abccf7df5b11c6c16853d5e5de9db69`, sürüm 0.17.0; Python 3.13 image ve provider/auxiliary alias kaynak kodu kontrol edildi. AIAgent gerçek import'u, OAuth hesap kataloğu ve iki gerçek model çağrısı geçti. Varsayılan mevcut Hermes kurulumu kullanılmaz/değiştirilmez.
- Model kilidi: `gpt-6-luna`, reasoning `high`, `openai-codex`, `codex_responses`, habnews'in kendi OAuth grant'i. API key, alternatif sağlayıcı/model, credential-pool taşıması ve hız kredisi yok.
- Araçlar: AIAgent için boş allowlist. HTTP kaynak okuma deterministik uygulamada; otomatik Commons araması kapalı. Hermes verilen kanıtlarla olgu/yazım işini yürütür; DB/onay/outbox/Telegram yetkisi yoktur. Kullanılmayan auxiliary çağrılar devre dışı yürütme yolundadır; savunma amaçlı tüm tanımlı yönlendirmeler aynı model/sağlayıcıya kilitlidir.

## Yerel offline deneme

Mevcut Hermes venv'ini kullanmayın. Yeni bir venv içinde:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/python -m pytest -q
.venv/bin/python -m habnews.cli dry-run
.venv/bin/python -m habnews.cli --db state/habnews.sqlite status
.venv/bin/python -m habnews.cli --db state/habnews.sqlite stop
```

Dry-run kendi geçici DB'sini kullanır. Fixture verileri TEST/SENTETİK etiketi taşır, gerçek haber/model yanıtı değildir. Gerçek Telegram mesajı göndermez. Rapor: `reports/DRY_RUN.json`. 7 Ekim 2026 görsel düzeltmesinde Türkiye filtresi dahil **237 test geçti**. Canlı kaynak/model durumu: [STATUS.json](reports/STATUS.json); görsel kabul kaydı: [PHOTO_DELIVERY_AUDIT.json](reports/PHOTO_DELIVERY_AUDIT.json).

## Dosyalar

- `habnews/`: collector, normalization, event dedup, evidence/numeric checks, job broker/runner, image rights/store, approval/outbox, budget, health/local CLI ve retention/backup.
- `sources.yaml`, `schemas/result.json`, `habnews/policy.txt`: sürümlü kaynak/policy/schema.
- `deploy/`: ayrı OS kullanıcısı ve servis, Compose, role-specific egress, sabit Hermes checkout, gizli OAuth girişi ve hedef kabul kontrolleri.
- `RUNBOOK.md`: bot/OAuth girişi, başlatma/durdurma, belirsiz gönderim, yedek/restore, geri alma.
- `SOURCE_VALIDATION.md`, `ISOLATION.md`, `ACCEPTANCE.md`, `COSTS.md`: gerçek durum ve sınırlar.

## V1'in bilinçli kısıtları

Ana HTML metni tamamen HTTP ile okunur ve kısa ömürlü özel job spool'u üzerinden AIAgent'e aktarılır. Tam metin arşivlenmez; geçici kaynak dosyası 5 dakika TTL taşır, tamamlanan job girdisi silinir ve backup'a girmez. Kalıcı kanıt, taslakta kullanılan kısa pasajlarla sınırlıdır (kaynak başına en fazla 3200 karakter). Otomatik doğrulayıcı, gövde cümlelerini bu pasajlara birebir bağlar; başlık kaynak başlığına, tam bir ara başlığa veya tam olgu cümlesine bağlıdır; sayılar aynı taslağın olgu cümlelerinde de bulunmalıdır. Serbest paragraf paraphrase doğrulaması ve ek PDF/video/OCR adaptörleri hazır değildir, doğrulanamayan iş `needs_review` kalır. Serbest paraphrase doğrulaması daha dar tutulduğu için doğrudan kaynak cümleleri kullanılan taslaklar oluşabilir.

TCMB ana sayfa kartları dışında HMB, BIST, BDDK, Resmî Gazete ve TÜİK için production parser/endpoint henüz doğrulanmadı. Dört X hesabı halka açık RSS ile canlı kart üretir. Genel serbest web araması yoktur. Kaynak kartı teyit beklemez; kullanıcı tarafından istenen tek kaynak taslağı açık atıf taşır, bağımsız teyit edilmiş sayılmaz. AA/Reuters işaretleri ve çok benzer pasajlar ortak aileye düşer; tüm sendikasyon ilişkileri kesin belirlenemez. Makro olaylar ve tam başlık eşleşmesi kümelenir; genel semantik olay dedup'u tamamlanmadı.

Görsel hattı modelden ayrıdır. Aynı haber sayfasının ana görseli yalnız önceden doğrulanmış yayıncı/CDN hostlarından okunur; kaynak metninin digest'iyle bağlanır, MIME/magic/decode/boyut ve yükleme hash'i denetlenir. WEBP/PNG görseller tam kadraj korunarak JPEG'e dönüştürülebilir; yapay görsel veya watermark kaldırma yoktur. Özel kaynak önizlemesi `rights_status=unknown`, `delivery_scope=private_source_preview` taşır ve onaylanan yeniden yayınlama paketine fotoğraf olarak eklenmez. Yeniden kullanım izni doğrulanan `verified_reusable` fotoğraflar için ayrı lisans/atıf yolu korunur. Haberin kendi görseli yoksa doğrulanmış TCMB arşiv fotoğrafı uygun bağlamda, arşiv etiketiyle kullanılabilir; başka durumda yalnız metin gönderilir.

Hermes'in bu sürümü Codex backend'inde standart output-token cap'i kaldırıyor. Adapterin açık `max_output_tokens` override'ı gerçek backend'de doğrulandı: 32-token testinde incomplete/max_output_tokens ve 32 output token alındı. Normal iş cap'i 8000; taşıma hata verirse `needs_review`, alternatif modele geçiş yok. Karakter/input/turn/deadline sınırları yerel olarak var; görünmeyen reasoning token tüketimi için kesin hard cap iddiası yoktur. Bu kurulumda gerçek çıktı sınırı testi geçti.

Mevcut botla global dedup ve gerçek exactly-once Telegram teslimatı garanti edilmez. Aynı ChatGPT hesabının kullanım limitleri ortak etkilenebilir. Kalan gerçek Pro kotası desteklenen veri yokken **bilinmiyor** gösterilir.
