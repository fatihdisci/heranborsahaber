# ENDEKS HABER geçişi

Bu dal mevcut sistemi dönüştürür. Yeni bot, ikinci Telegram tüketicisi veya yeni Cloudflare kaynakları oluşturulmaz. X otomatik yayını yoktur. Profil/banner dış hesaba otomatik yüklenmez.

## Dosyalar ve çalışma şekli

- Kimlik: `src/brand.ts`, `src/brand-profile.ts`; `assets/profile.png` (800×800), `assets/banner.png` (1500×500) ve SVG asılları.
- Kartlar: `src/card.ts`; altı kalıcı yerleşim, iki tema, 1080×1350 PNG. Son dakika ve devre kesici ayrı başlık rozetleri taşır. Diğer türlerde ek görsel kalabalık oluşturulmaz.
- Editoryal: `src/editorial.ts`, `src/style.ts`, `sources.json`. Önemli KAP/BIST > Türkiye para politikası/verileri > yatırımcıya etkili küresel finans. Genel teknoloji için daha yüksek konu eşiği kullanılır; dünya haberleri kaldırılmaz.
- Devre kesici: `src/kap/store.ts`, `src/kap-delivery.ts`; bütün donmuş üyeler okunur, tek iş/tek mesaj hazırlanır, güncel tercih teslimatta tekrar kontrol edilir.
- Güvenli güncelleme: haber ve KAP kurulumları aynı staging/başlangıç/geri dönüş mekanizmasını kullanır; normal kurulum çalışan sürümü değiştirmez, `--update` gerekir.

## Mac mini'de kontrollü geçiş

Geliştirme sırasında canlı sürüm `4e24afd` ve iki çalışan servis gözlendi. Bu belge bir deploy makbuzu değildir; geçiş anında yeniden durum kontrolü yapılmalıdır.

1. Canlı sürümü, iki servis PID'sini, kuyruk/lease durumlarını, disk alanını ve mevcut KAP tercihlerini kontrol et. Modelde aktif iş varsa tamamlanmasını bekle. Yeni model lease'lerini geçici duraklatırken önceki değeri kaydet.
2. İki SQLite dosyasını SQLite backup API ile tutarlı yedekle; DB dosyalarını silme veya eski kopyayla değiştirerek geri sarma. Mevcut servis/plist ve sürüm kaydı korunur.
3. Devre kesiciyi geçiş boyunca kapalı tut. Eski kayıtları yeniden kuyruğa alma. Haber servisini `python3 scripts/install_local.py --update`, bağımsız toplayıcıyı `python3 scripts/install_kap.py --update` ile ayrı ayrı geçir. Kurulumlar temiz staging'de bütün kontrolleri yapar; hazır sinyali ve release kimliği doğrulanmadan döngüler başlamaz. Başlangıç hatasında önceki dosyalar geri döner.
4. Yeni servis hazır dosyalarını ve kaynak/Telegram/KAP sağlığını doğrula; geçici model duraklatmasını yalnız kendi koyduğun değer hâlâ geçerliyse geri al.
5. Mevcut KAP tercihlerini kopyala ve yalnız istenen alanları değiştir: `circuitNotifications=true`, `priorityIndices=true`; `otherCompanies=topics` kullanılıyorsa var olan konulara `circuit` ekle. Bütün tercihleri örnek dosyayla körlemesine değiştirme. Tercihi `node --import tsx scripts/kap_service.ts --preferences /güvenli/yol/tercihler.json` ile uygula. Bu komut Telegram tüketicisi başlatmaz. Etkinleştirme zamanı kalıcı kaydedilir; eski devre kesiciler canlanmaz.
6. Bundan sonra yayımlanan ilk uygun devre kesicide grup üyeleri, kaynak kanıtı ve tek mesaj makbuzunu kontrol et. İlk gerçek bildirim gelmeden canlı devre kesici teslimatı başarıyla çalıştı denmez. Test amacıyla eski kayıtları oynatma.
7. X kullanıcı adını ve profil/banner yüklemesini hesap sahibi yapar. Telegram botunun dış görünen adı gerekiyorsa ayrıca ENDEKS HABER olarak değiştirilir; kullanıcı adı ve erişimler aynıdır.

## Geri dönüş

Her servisin `backups/update-<kimlik>/rollback.json` dosyası önceki app/plist yollarını tutar. Önce ilgili servisi durdur, bekleyen Telegram update ve dış teslimat makbuzlarını uzlaştır, eski dosyaları ters sırayla geri al ve yalnız o servisi başlat. Cursor, offset veya DB yedeğini geri sarmak geçmiş mesajları tekrar gönderebilir; yapılmaz. Devre kesiciyi kapatmak gönderilmemiş grupları susturur, kaynak kayıtlarını silmez. Yeni kategori/şablonların bulunduğu taslaklar nedeniyle eski koda geri dönüşte bu taslaklar ayrıca uzlaştırılmalıdır.

## Doğrulama

`npm ci --ignore-scripts`, TypeScript kontrolü, Node testleri, Python testleri, native macOS OCR ve dry-run build canlı sırlara ihtiyaç duymaz. `test/endeks.test.ts` 84 kombinasyonun gerçek PNG'sini üretir. `test/kap-delivery.test.ts` donmuş devre kesici grubundan tam kaynak → model sözleşmesi → gerçek PNG → taklit Telegram gönderimi → tek makbuz akışını sınar. Gerçek bot mesajı veya yeni AI çağrısı test amacıyla yapılmaz. Görsel galerisindeki rakamlar/şirketler çevrimdışı örnektir.
