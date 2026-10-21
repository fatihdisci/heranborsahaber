# SECTOR HABER

Türkiye ve dünya ekonomisi, finans, şirketler, teknoloji ve önemli küresel gelişmeler için Telegram haber masası. Bu repo yalnız güncel SECTOR HABER uygulamasını içerir. Uygulama ve bağımlılıkları [`sector/`](sector/README.md) altındadır.

## Güncel sistem

- Haberler önce başlık ve özet olarak gelir. **Tweet ve görsel oluştur** düğmesi tam kaynak metninden Türkçe içerik hazırlar.
- Bağımsız [KAP toplayıcısı](sector/KAP.md), seçilen bildirimleri toplar; ana metin, tablolar ve PDF ekleri içerik üretiminde incelenir.
- Bota doğrudan haber metni, desteklenen bağlantı veya PDF gönderilebilir. Hazırlanıyor mesajı tamamlandığında aynı mesajda tweet ve görselle değiştirilir.
- Altı kart yerleşimi ve iki renk teması kullanılır. **Kartı yeniden tasarla** aynı mesajın görselini değiştirir; yeniden AI çağrısı yapmaz.
- İçerik üretimi ayrı Hermes profili üzerinden `gpt-6-luna` / `high` ile çalışır. Telegram işlemleri yalnız kayıtlı sahibine açıktır. **X yayını yoktur.**

## Geliştirme ve doğrulama

Node.js 22 ile:

```sh
cd sector
npm ci --ignore-scripts
npm run check
npm test
npm run build
```

PDF testleri için `sector/requirements-pdf.txt` bağımlılıklarının kurulu olduğu Python ortamında, yine `sector/` dizininden:

```sh
python3 -m unittest discover -s test -p 'test_*.py'
```

Build yalnız deneme derlemesidir; bu kontroller gerçek Telegram veya X gönderimi yapmaz. Kaynak erişim denemeleri ve canlı kurulum ayrı işlemlerdir.

## İşletim ve dosyalar

- [Kurulum, haber akışı ve Telegram davranışı](sector/README.md)
- [KAP toplama ve filtreleme kuralları](sector/KAP.md)
- [Merkezi haber kaynakları](sector/sources.json)
- [Editör promptu ve doğrulama](sector/src/editorial.ts)
- [Kart çizimi](sector/src/card.ts), [yerleşim seçimi](sector/src/card-layout.ts) ve [marka dosyaları](sector/assets/)

Canlı servisler Mac mini'de `~/Library/Application Support/sector-haber/` altında, depodan ayrı çalışma kopyalarıyla çalışır. Repo adı değişikliği veya Git pull/push canlı servisi yeniden başlatmaz. `sector/` uygulama dizini ve servis yolları korunur. MacBook üzerinden geliştirmede ikinci bir bot tüketicisi başlatılmamalıdır.

Gizli bilgiler, Hermes oturumu, canlı veritabanları ve medya Git'e eklenmez. SECTOR'a ait Cloudflare yapılandırması korunur; aktif çalışma ortamı Mac mini'dir. Önceki uygulamanın kaldırılan dosyaları gerektiğinde Git geçmişinden incelenebilir.
