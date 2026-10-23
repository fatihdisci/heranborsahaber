ENDEKS HABER — Normal ChatGPT sohbeti için taşınabilir kart paketi

1. ZIP'i ChatGPT'ye yükle. CHATGPT-PROMPT.txt içeriğini ilk mesajına yapıştır.
2. Haber metnini, KAP belgesini, tabloyu veya görseli ekle. İstersen “yalnız alınanlar” de.
3. Kod/dosya çalıştırabilen sohbet motoru render.mjs ile PNG oluşturabilir. Çalıştırma özelliği bulunmayan sohbetin yalnız dosya yükleyerek PNG üreteceği garanti değildir.

DOSYALAR
render.mjs: hazır çevrimdışı PNG/SVG üreticisi (Node 18+). npm/API/Telegram gerekmez.
runtime/cards.mjs: canlı kaynak kodundan derlenen gerçek kart motoru.
runtime/index.mjs + index_bg.wasm: paketlenmiş PNG dönüştürücü.
src/card-pages.ts: ortak 1–4 kart bölme motoru.
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
Ortak motorun kart başına güvenli kapasitesi kurum tablolarında 10, AKD/takas tablolarında 5, günlük raporda 15, devre kesici kod gridinde 36 satır/koddur. Aşımda aynı veri dengeli 2–4 karta bölünür. Büyük geri alım tablosu kart başına en çok 60 satır kullanır; 54 satırlı mevcut rapor tek kart kalır. Satır kesme, gereksiz yazı küçültme ve otomatik thread yok; dört kart kapasitesi de aşılırsa açık hata verilir.

KAYNAKTAN YENİDEN ÜRETİM
Kaynak repoda Node 22 kullan: npm ci --ignore-scripts && npm run kit:export. Komut temiz geçici staging alanında kaynakları ve varlıkları kopyalar, runtime'ı derler, 19 örnek PNG üretir, SHA256 manifestini doğrular ve ZIP'i oluşturur. ZIP içindeki src/ dosyaları esbuild ile yeniden derlenebilir.

Kaynak repo: sector/src/ ve sector/assets/ (repo kökü altındaki sector dizini).
Paket canlı veritabanı, kuyruk, hesap, bot veya Hermes erişimi içermez. Sohbetin ürettiği içerik canlı bot akışına kendiliğinden eklenmez.

Ortak çıktı tercihi: content.json içindeki output_preferences list/side/count/show_time/show_footer alanları seçilen satırları belirler. Tüm liste talebinde list=all kullanın. render.mjs kapasite hatası verirse satırları özetlemeyin veya azaltmayın; dört okunaklı görsele de sığmadığını belirtin. Kaynak satırlarının eksiksizliği ayrıca doğrulanmalıdır; renderer kaynak doğrulaması yapmaz.

Çıktı tercihleri alan bazında güncellenir: belirtilmeyen list/count/side/show_time/show_footer/presentation önceki değerini korur. Saat, alt not veya yalnız alış/satış isteği listeyi “tümü”ne dönüştürmez. İlk N için yalnız 1–999 arasında tam sayı desteklenir; 1000 gibi destek dışı değeri 100'e kısaltma, açık hata ver. Alan belirtilmemişse mevcut ürün varsayılanını koru. Genel geri alım kartında show_footer=false isteğe bağlı dipnotları gizler; kısmi toplam ve eksik hücre işaretleri korunur. Eksik/kısmi veri ayrıntıları editör kaynak notlarında kalmalıdır.

İş Yatırım günlük pay geri alımı tablosu: card_data.report.buyback alanında day (ISO işlem tarihi), row_count, reader ve rows yer alır. Her satır ticker, day (GG.AA.YYYY), nominal, price, amount, raw alanlarını taşır. Kaynağın nominal miktarını lot/adet olarak yeniden adlandırma. Fiyat ve toplam tutar boşsa null / — koru; çarpımla toplam üretme. Görsel bütün satırları içerir; tweet en fazla 10 farklı hisse içerir ve görseli filtrelemez. Tarihli doğrulanmış BIST30 → BIST100 → diğer sırası, grup içinde nominal miktar azalan ve kod artan kullanılır. Üyelik bilinmiyorsa tahmin edilmez. Görselde yalnız büyük PAY GERİ ALIMLARI başlığı, işlem tarihi ve sütunlu tablo; kaynak, saat, dipnot yoktur. Okunabilir kapasite aşımında hata ver; satır atma. Paket kaynaktan veri çekmez, verilen tabloyu render eder.

ÇOKLU KART: Ortak cardSvgs/draftCards üreticisi aynı değişmez veriyi okunaklı 1–4 PNG olarak böler. Başlıkları küçültme; satırları kesme. render.mjs birden fazla kartta kart-1.png, kart-2.png vb. üretir. Bütün görseller tek tweetin ekidir; Telegram’da tek albüm ve tek kontrol mesajı kullanılır. Tweet kısa özet olabilir; görseller seçilen bütün satırları taşır. Açık tüm-hisseler-tweette isteği X metin sınırını aşarsa sessiz kesme yapma: kısa özet/kapsam daraltma için editöre açık uyarı ver. Dört karta sığmayan veri için de açık kapasite uyarısı ver; kendiliğinden thread oluşturma. Geri alımın endeks öncelikli en çok 10 hisse tweet kuralı korunur.
