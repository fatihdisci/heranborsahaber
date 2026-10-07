# Son canlı kaynak genişlemesi — 6 Ekim 2026

Tam metin araştırmasına açık: **Foreks, Bloomberg HT, Habertürk, Sözcü, Dünya, Ekonomim, TCMB**. Her kaynağın canlı poll'u başarılı ve baseline kaydı var. Sözcü eski `/rss/ekonomi.xml` adresi genel içerik döndürdüğünden yayıncının resmî `/feeds-rss-category-ekonomi` adresi seçildi. Bloomberg HT/Habertürk/Sözcü/Dünya/Ekonomim listeleri ve örnek ana metinleri HTTP200, ana metin parseri geçti. Kaynak sayısını artırmak günlük model/ücretli araç bütçesini artırmadı.

**Investing:** yayıncının RSS sayfasında ilan ettiği `/rss/news.rss` aktif, 10 kayıt. Hem analiz hem haber makaleleri403, robots403; gözlem RSS ile sınırlı. Bu source metadata'sı `article_access=blocked_http_403`; araştırma kuyruğu ve LLM taslağı oluşturulmaz, var olan araştırma da fetch yapmadan durur. RSS metni doğrulanmış tam haber gibi sunulmaz. Erişim engeli aşılmadı.

Haber metinleri kısa ömürlü, sahibine özel inceleme; kaynak bağlantısı korunur. Görsel veya kamuya yayın hakkı varsayılmaz. 130 test geçti. Rapor: `reports/source-expansion.json`. Dağıtım paketindeki bütün kaynaklar varsayılan kapalıdır; kurulu instance ayrı canlı config kullanır.

---

# Kurulu Mac instance kaynak durumu

6 Ekim 2026: Foreks ve TCMB özel kullanıcı incelemesi için aktif. Container içinden liste ve makale erişimi 200; iki parser geçti. Foreks robots ve AI/RSS ilanı, TCMB kaynaklı bilgi kullanım koşulları incelendi. Tam metin geçici TTL300, kısa evidence ve kaynak URL; görsel/yayım hakkı varsayılmaz. Raporlar: `container-source-smoke.json`, `source-access-review.json`. TCMB robots isteği 404 verdi; sayfanın açık kullanım koşulları ayrıca okundu. Bu kurulum ticari yayın yapmaz.

Dağıtım paketinin `sources.yaml` dosyası tüm kaynakları kapalı bırakır. Kurulu instance ayrı config'inde yalnız Foreks ve TCMB aktiftir. Aşağıdaki önceki keşif raporu diğer kaynakların neden kapalı kaldığını gösterir.

# Kaynak doğrulaması — 6 Ekim 2026

Kontroller bu macOS hosttan, az sayıda salt-okunur HTTPS isteğiyle yapıldı. HTTP 200 izin/lisans, parser başarısı eksiksiz kapsama garantisi değildir. Tam haber içerikleri raporda arşivlenmedi; metadata, uzunluk ve hash kaydedildi. Ayrıntılı UTC zaman/status/MIME/final URL: `reports/source-smoke.json`, `reports/article-smoke.json`, `reports/official-discovery.json`, `reports/tcmb-smoke.json`.

| Kaynak | Feed/listing | Örnek ana metin | Runtime |
|---|---|---|---|
| Foreks | 200, RSS, 100 entry | 200, okunabilir HTML main, 1220 karakter | disabled; kullanım/retention kabulü bekliyor |
| Bloomberg HT | 200, XML, 50 entry; gerçek final `/rss/tum-haberler.xml` | 200, okunabilir HTML main, 548 karakter | disabled; kullanım/retention kabulü bekliyor |
| Investing Türkiye | 200, RSS, 10 entry | **403**, bypass denenmedi | disabled; article blocked |
| Habertürk Ekonomi | 200, XML, 30 entry | 200, okunabilir HTML main, 5614 karakter | disabled; kullanım/retention kabulü bekliyor |
| Sözcü Ekonomi | 200, XML, 50 entry | 200, HTML main; seçilen feed girdisi spor haberi çıktı | disabled; feed kapsamı güvenilmez, deterministic finans/Türkiye filtresi zorunlu |
| TCMB | Resmî home 200; basın sayfası resmî home'dan keşfedildi; 10 duyuru kartı parse | Gerçek resmî faiz açıklaması 200; main 2270 karakter | `tcmb_home` parser hazır, disabled; hak/retention kabulü bekliyor |
| HMB | Resmî home 200, robots okunabildi | Yayın endpoint/main parser henüz doğrulanmadı | discovery_only, disabled |
| Borsa İstanbul | Resmî home 200, robots okunabildi | Yayın endpoint/main parser henüz doğrulanmadı | discovery_only, disabled |
| BDDK | **TLS certificate verification failure** | Güvenlik gevşetilmedi | disabled/degraded |
| Resmî Gazete | Resmî home 200, robots okunabildi | Duyuru/regülasyon seçici parser doğrulanmadı | discovery_only, disabled |
| TÜİK | Resmî home 200; haber linkleri görüldü, veri kartları JS/# linkleri | Bülten API/detail ve dönem parseri doğrulanmadı | discovery_only, disabled |

**Enabled kaynak: 0.** Erişilebilir feedler mümkün adaydır; canlı olduğuna dair yanlış işaretleme yoktur. HMB/BIST/TÜİK/Resmî Gazete adaptörünün eksik kalan kısmı model/bot secret'ından bağımsız production parser doğrulamasıdır. Bu teslimat bu kurumların bütün yayınlarını izleyen tamamlanmış bir feed envanteri değildir.

TCMB URL yılı kaynaktan dinamik alınır; 2026 ve 2027 fixture'larıyla test edildi. Yalnız ana sayfada görünen kartlar vardır; birden fazla yeni duyuru bu görünüm dışına düşerse kaçabilir. Basın arşivinin JS endpoint'i icat edilmedi. Date-only açıklamada “yayın saati belirtilmiyor / yeni görüldü” gösterilir; gece yarısı yayın saati sayılmaz.

RSS kaynaklarının bugün erişilebilir olması full metin/görsel yeniden paylaşım hakkı değildir. Robots koşulları endpoint bazında ve veri retention/kısa alıntı kullanım şartları ayrıca kabul edilmelidir. AA/Reuters ücretli akış, X/Nitter, sosyal hesap doğrulaması ve fotoğraf aboneliği açılmadı. Cumhurbaşkanı/ekonomi yönetimi görev ve hesap mapping'i canlı doğrulanmadığından kişiye özel adapter/rol listesi sabitlenmedi.

KAP/SPK discovery/polling/arama/PDF adapteri yoktur. Yasak domainler runtime HTTP ve kaynak sorgusu filtresinde engellenir; medyadaki rutin disclosure tekrarları conservative scope_excluded olur. Genel medya ile eski bot arasında çakışma sürebilir; global dedup yoktur.

Resmî referanslar: [Hermes Python library](https://hermes-agent.nousresearch.com/docs/guides/python-library), [providers](https://hermes-agent.nousresearch.com/docs/integrations/providers), [profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles), [Telegram Bot API](https://core.telegram.org/bots/api), [OpenAI models](https://learn.chatgpt.com/docs/models), [OpenAI authentication](https://learn.chatgpt.com/docs/auth). Model dokümanı hesap erişimini kanıtlamaz; yeni OAuth kataloğu ve gerçek smoke zorunludur.
