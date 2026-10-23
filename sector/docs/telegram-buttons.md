# Telegram düğme rehberi

Metni kopyala (📋) düğmesi kaldırıldı. Tweet metni Telegram'ın kendi metin seçme/kopyalama özelliğiyle alınabilir. Düğmeler içerik türüne ve yayın durumuna göre görünür; hepsi her kartta çıkmaz.

## Hazır tweet ve görsel kartında

| Düğme | İşlev |
|---|---|
| 🔗 | Haberin veya bildirimin kaynak bağlantısını açar. |
| ✏️ | Tweet ve görsel metnini düzenlemek için talimat ister. Yeni içerik mevcut kaynak ve sayı kontrollerinden geçer. |
| 🎨 | Desteklenen şablonlarda yerleşim seçme menüsünü açar. Devre kesici ve rapor gibi sabit düzenlerde gösterilmez. |
| 🚀 | Açık paylaşım onayıdır: tweet ve görseli X API paylaşım kuyruğuna alır. Günlük 20 API paylaşımı bütçesi, güncel revision, süre ve tekrar korumaları uygulanır. X bağlantısı etkin olduğunda gösterilir; geçerlilik basıldığında yeniden denetlenir. Bu düğmeye basmak gerçek yayın isteğidir. |
| ✅ | Elle X'e gönderdiğin içeriği paylaşıldı işaretler. Günlük yayın sayacı ve zaman aralığı uyarısı güncellenir. X'e gönderim yapmaz. |
| ⏸ | İçeriği ertelendi işaretler. Zamanlı gönderim planlamaz ve X'e paylaşmaz. |
| 📊 | Bugünkü toplam, manuel/API ayrımı, API bütçesi, son yayın ve paylaşım aralığı önerisini gösterir. |
| 🖼 | Kartın sıkıştırılmamış orijinal PNG dosyasını Telegram belgesi olarak gönderir. Panoya kopyalamaz; AI çağırmaz. |
| 🧾 | Editör için kaynakları, iddiaların dayanaklarını, veri dönemini, belirsizlikleri ve kaynak notlarını açar. Paylaşım görseline yazı eklemez. |
| 🔎 | Kartta okunan tablo satırlarını ve mevcutsa değer/birim/yön/dönem alanlarını gösterir. |
| 🔧 | Desteklenen tablo hücresini düzeltmek için yanıt ister; örnek `buy.0.value = 123 lot`. Önce/sonra farkı kaydedilir, mevcut denetimle yeniden hazırlanır. Kullanıcı düzeltmesi resmî teyit sayılmaz. |
| 📄 | Genel geri alım raporunun bütün satırlarını CSV dosyası olarak verir. |

## Yayınlandı veya ertelendi durumunda

| Düğme | İşlev |
|---|---|
| ☑️ | Paylaşıldı durumundaki kartın yayın özetini/sayacını gösterir. |
| 🕒 | Elle paylaşıldı işaretlenen içeriğin yayın saatini düzeltmek için yanıt ister. İstanbul saati kullanılır. API yayınının saatini değiştirmez. |
| ↩️ | Manuel paylaşıldı işaretini geri alır. X'teki tweeti silmez; API yayınını geri almaz. |
| ▶️ | Ertelendi işaretini kaldırıp içeriği hazır duruma döndürür. X'e göndermez. |

## Tasarım menüsünde

| Düğme | İşlev |
|---|---|
| 🎲 | Mevcut yerleşimden farklı desteklenen bir düzeni rastgele seçer. Tweet ve kanıt metni değişmez. |
| editorial | Standart yayın yerleşimini seçer. |
| frame | Çerçeveli yerleşimi seçer. |
| rail | Sol dikey şeritli yerleşimi seçer. |
| masthead | Üst başlık bloğu ağırlıklı yerleşimi seçer. |
| center | Ortalanmış başlıklı yerleşimi seçer. |
| brief | Bantlar ve alt bilgi bloğuyla kısa haber yerleşimini seçer. |

## Haber önizlemesinde

| Düğme | İşlev |
|---|---|
| 🔗 | Kaynağı açar. |
| ✨ | Haberin tam metnini okuyup tweet ve görsel hazırlamasını ister. Aynı istek iki kez model işi oluşturmaz. |
| ℹ️ | Yeni haber filtresinin rota kararını, gerekçelerini, eşleşme güvenini ve olay kaynaklarını gösterir. |
| 👎 | “İlgisiz” geri bildirimi kaydeder. Kaynağı veya şirketi otomatik susturmaz. |
| 🔁 | “Tekrar haber” geri bildirimi kaydeder. Tweeti/kartı yeniden üretmez. |
| 🕓 | “Acil değil / seçkilik” geri bildirimi kaydeder. Tek başına rotayı değiştirmez veya seçki gönderimini açmaz. |
| Seçkideki haber başlığı | Seçilen haber için mevcut tam kaynak/model/denetim akışını başlatır. |
| Mesaj gelmediyse yeniden gönder (çift olabilir) | Yalnız belirsiz teslimatta gösterilir. Hazır içeriğin yeniden teslimini açıkça onaylar; ilk mesaj gelmişse kopya oluşturabilir. Yeni AI üretimi değildir. |

“Haber paneli” menü düğmesi mevcut Mini App'i açar. Otomatik filtre gölge modda, otomatik seçki kapalıdır. Geri bildirim düğmeleri bunları etkinleştirmez.
