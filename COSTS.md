# Yük ve maliyet

Bu oturumda yeni VPS, barındırma, model API anahtarı, ücretli search/vision/extract veya ek ChatGPT kredisi satın alınmadı. Yerel offline testlerin ek sağlayıcı gideri yoktur. Bu kurulum için beş gerçek Pro model çağrısı yapıldı (iki reasoning smoke ve üç output-cap test denemesi), yerel günlük kota defterine kaydedildi; Codex geliştirme sohbeti kendi hesabınızın kullanımını etkileyebilir.

- Yeni haber runtime: aynı ChatGPT Pro hesabı, OAuth `gpt-6.1-sol`. API token fiyatı üzerinden dolara çevrilmez. Mevcut Hermes/Codex'le hesap limitleri ortak etkilenebilir; Pro sınırsız sayılmaz. Kalan gerçek kota/reset veri yoksa bilinmiyor.
- Yerel güvenlik sınırı: günde en çok 60 LLM isteği, 6 P0 rezervi, tek eşzamanlı LLM olayı, olay başına 6 tur üst sınırı. Bu hesap kotası garantisi değildir. Low/medium smoke iki gerçek istektir. Fallback/otomatik ek kredi yok.
- Ek tool bütçesi: günlük **0 USD**, aylık **0 USD**. Paid adapter disabled; API key verilerek etkinleştirilemez. İlerde ücretli adapter ayrıca fiyat sürümü/upper reservation/provider hard-limit geliştirmesi ve açık yetki gerektirir.
- Barındırma: mevcut hostun mevcut elektrik/internet/disk/VM maliyeti burada bilinmiyor. Linux container host yoksa hazır paket çalışmaz; otomatik satın alma veya maliyet taahhüdü yok.

İzin verildiğinde beş feed @120 saniye ≈150 feed GET/saat, TCMB home @180 saniye ≈20 listing GET/saat: toplam ≈170 conditional kontrol/saat. Haber sayısına göre ana sayfa/article revalidation ve Commons discovery eklenir. Şu an enabled=0 → sürekli polling/LLM yükü 0. Başlangıç maks20 kaynak/HTTP üst concurrency4; mevcut collector ve Unix broker fiilen seri olduğundan HTTP concurrency1'dir, daha düşük yük karşılığında latency artabilir. Source başına concurrency1 korunur. P0/P1 ilk görülmeden30–90s hedefi doğrulanmış SLA değildir.

P1 en fazla6 paket/saat,30/rolling24h; >100 bekleyen onayda backpressure. P0 mesaj gürültü limitinden muaf, kaynak/model bütçesinden muaf değildir. Local80% incident tek uyarı;100% reservation durur. Model timeout/ücret belirsizliği uncertain olur, kör retry yapılmaz.

Docker paketinde runner2GiB, uygulama rolleri512MiB limitleri ve private disk kullanımı vardır. Bunlar ölçülmüş gerçek minimum kapasite değildir. 90g observation hash/metadata,180g draft/decision/audit,30g evidence/media TTL; aktif review korunur. Disk dolma senaryosu mock ile test edildi; gerçek host kapasite/backup maliyeti ayrıca izlenmelidir.
