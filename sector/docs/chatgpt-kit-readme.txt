ENDEKS HABER — Normal ChatGPT sohbeti için taşınabilir kart paketi

1. ZIP'i ChatGPT'ye yükle. CHATGPT-PROMPT.txt içeriğini ilk mesajına yapıştır.
2. Haber metnini, KAP belgesini, tabloyu veya görseli ekle. İstersen “yalnız alınanlar” de.
3. Kod/dosya çalıştırabilen sohbet motoru render.mjs ile PNG oluşturabilir. Çalıştırma özelliği bulunmayan sohbetin yalnız dosya yükleyerek PNG üreteceği garanti değildir.

DOSYALAR
render.mjs: hazır çevrimdışı PNG/SVG üreticisi (Node 18+). npm/API/Telegram gerekmez.
runtime/cards.mjs: canlı kaynak kodundan derlenen gerçek kart motoru.
runtime/index.mjs + index_bg.wasm: paketlenmiş PNG dönüştürücü.
src/card.ts: haber kartları ve altı yerleşim.
src/market-card.ts: sabit devre kesici, kurum, AKD, takas, hacim şablonları.
src/brand.ts: renkler ve E marka işareti.
src/: kart motorunun tüm transitif yerel TypeScript bağımlılıkları; temiz çıkarılmış ZIP'ten yeniden derlenebilir.
assets/: profil, banner, Noto Sans yazı tipleri ve font lisansı.
examples/: JSON + SVG + gerçek PNG referansları. ÖRNEK VERİLER KURMACADIR, YAYINLANMAZ.
CHATGPT-PROMPT.txt: kopyalayıp kullanacağın editoryal ve tasarım promptu.

ÇALIŞTIRMA
node render.mjs examples/haber-editorial-navy.json kart.png
JSON alanları: template, headline, body, theme, layout ve isteğe bağlı card_data.
Başlık/gövde görsel metnidir; tweet metni ayrı üretilir.
theme: navy | paper
layout: editorial | frame | rail | masthead | center | brief
Devre kesici bu seçimlerden bağımsız daima navy/editorial kullanır.
card_data: ticker, tickers, broker, as_of, buy/sell/holdings [{label,value}], metrics [{label,value}].
Tek kart motorunun güvenli kapasitesi kurum tablolarında 10, AKD/takas tablolarında 5 satırdır. Daha çok satır varsa hiçbir hisseyi atma veya tweet metninde özetleyerek görsel listesini eksiltme: mevcut motor kapasite aşımında açık hata verir. Tek görsele sığmıyorsa açık kapasite uyarısı ver. Kullanıcı ayrıca karar vermeden çoklu kart/thread üretme. Devre kesicide 120 kod test edilmiştir; kapasite aşımında motor hata verir, sessizce kod silmez.

KAYNAKTAN YENİDEN ÜRETİM
Kaynak repoda Node 22 kullan: npm ci --ignore-scripts && npm run kit:export. Komut temiz geçici staging alanında kaynakları ve varlıkları kopyalar, runtime'ı derler, 19 örnek PNG üretir, SHA256 manifestini doğrular ve ZIP'i oluşturur. ZIP içindeki src/ dosyaları esbuild ile yeniden derlenebilir.

Kaynak repo: sector/src/ ve sector/assets/ (repo kökü altındaki sector dizini).
Paket canlı veritabanı, kuyruk, hesap, bot veya Hermes erişimi içermez. Sohbetin ürettiği içerik canlı bot akışına kendiliğinden eklenmez.

Ortak çıktı tercihi: content.json içindeki output_preferences list/side/count/show_time/show_footer alanları seçilen satırları belirler. Tüm liste talebinde list=all kullanın. render.mjs kapasite hatası verirse satırları özetlemeyin veya azaltmayın; tek görsele sığmadığını belirtin. Kaynak satırlarının eksiksizliği ayrıca doğrulanmalıdır; renderer kaynak doğrulaması yapmaz.

Çıktı tercihleri alan bazında güncellenir: belirtilmeyen list/count/side/show_time/show_footer/presentation önceki değerini korur. Saat, alt not veya yalnız alış/satış isteği listeyi “tümü”ne dönüştürmez. İlk N için yalnız 1–999 arasında tam sayı desteklenir; 1000 gibi destek dışı değeri 100'e kısaltma, açık hata ver. Alan belirtilmemişse mevcut ürün varsayılanını koru. Genel geri alım kartında show_footer=false isteğe bağlı dipnotları gizler; kısmi toplam ve eksik hücre işaretleri korunur. Eksik/kısmi veri ayrıntıları editör kaynak notlarında kalmalıdır.
