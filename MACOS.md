# Bu Mac'te kurulu haber botu

Güncel model: **gpt-6-luna**, düşünme açık, **reasoning effort high**. Kullanıcının model değişikliği uygulandı; ayrı OAuth hesabında gerçek high çağrısı başarılı. Otomatik düşük effort/model seçimi yok. Aşağıdaki ilk kurulum ölçümleri tarihsel kayıttır.

Yeni bot: https://t.me/habernewssbot. Tek numeric kullanıcı ve pozitif özel sohbet kimliğiyle sınırlandı. Token sadece 0600 özel dosyada ve yeni approval rolünün VM içindeki ayrı volume'undadır; dağıtım ZIP'ine girmez.

Çalışma dizini: `/Users/fatihdisci/Library/Application Support/habnews`. Ayrı Colima profili `habnews`, 2 CPU, 4 GiB RAM, 20 GiB sparse disk. Container UID 11001, LLM ve Telegram ayrı iç ağ/proxy, collector network none + kaynak Unix broker. Eski ev dizinleri, auth, SSH anahtarları, eski repository veya Docker socket uygulama container'larına verilmez. Yeni LaunchAgent: `com.heranborsa.habnews`; kullanıcı girişinde açılır. Mac yeniden başlatılmadı, mevcut hizmetler yeniden başlatılmadı.

Tam `gpt-6.1-sol` kendi OAuth oturumu ve normal hızla test edildi: low 2.959 s, medium 2.661 s; medium seçildi. Server effective model/request ID AIAgent tarafından bildirilmedi, raporda null. Çıktı sınırı gerçek backend'de 32 token ve incomplete/max_output_tokens ile doğrulandı; normal işler 8000 cap kullanır. Beş gerçek kurulum model çağrısı günlük yerel bütçeye kaydedildi; tüm hesabın gerçek kalan kotası bilinmiyor.

## Aktivasyon

Telegram'da gönderilen açık TEST/SENTETİK kartı sahibi tarafından **Onayla** düğmesiyle onaylandı. Bu yalnız özel kullanıcı/callback testidir, gerçek haber değildir ve hiçbir yere yayımlanmadı. Diğer kabul kontrolleri de geçince ilk haber takibi otomatik açıldı. Mevcut durum `enabled=true`. `/haber_durdur` bu bekleyen başlangıcı da iptal eder. İnsan onayı taklit edilmez.

Bu instance için **Foreks, Bloomberg HT, Habertürk, Sözcü, Dünya, Ekonomim ve TCMB** tam metin araştırması açık. **Investing** resmî haber RSS gözlemi açık; makale403 nedeniyle kanıt/LLM taslak üretimi kapalı. RSS özetleri tam haber metni gibi kullanılmaz. /haber_kaynaklar bu ayrımı gösterir. İlk kurulumda Foreks ve TCMB doğrulandı. Foreks RSS/ana metin 200, 100 entry; TCMB kartları/ana metin 200, 10 kart. Baseline mevcut eski haberleri göndermez; yeni uygun, yeterince teyitli gelişmeler taslak oluşturur. Diğer kaynaklar henüz kapalı; bütün kurum/haber kapsamının eksiksiz olduğu iddia edilmez. Görsel ancak yeniden kullanım hakkı ve konu eşleşmesi doğrulanırsa seçilir, aksi durumda kaynaklı metin gelir. Bu kurulum yalnız özel kişisel inceleme gönderir; haber onayı yayın değildir.

Paket sources.yaml varsayılanı bütün kaynaklar kapalıdır. Kurulu instance config'inde sekiz akış açıktır; yedisi tam metin araştırması, Investing yalnız RSS gözlemi yapar. Paket kodunda yapılan düzenleme kurulu runtime'a kendiliğinden uygulanmaz; yalnız habnews runtime'a senkronize edilip image yeniden derlenmelidir.

## İşletim

Telefon üzerinden: `/haber_durum`, `/haber_butce`, `/haber_kaynaklar`, `/haber_durdur`, hazır kabul sonrası `/haber_baslat`.

Bu paket dizininden:

```bash
deploy/macos.sh status
deploy/macos.sh compose exec -T collector python -m habnews.cli --db /data/habnews.sqlite health
deploy/macos.sh compose exec -T collector python -m habnews.cli --db /data/habnews.sqlite stop
```

Tam yeni stack'i kapatmak için önce haber durdurun, sonra yalnız `com.heranborsa.habnews` LaunchAgent'ını bootout ve yalnız `habnews` compose stack'ini stop edin. Genel Docker prune, eski Hermes kill/restart veya mevcut auth revoke yapmayın. Volume'larda DB/onay/medya ve yalnız runner'da yeni OAuth oturumu bulunur; backup auth/token içermez.

Yeni supervisor kendi ömrü boyunca `caffeinate -i` ile boşta uyumayı engeller; ekran kilidi/uykusu devam edebilir. Mac kapalıysa, kapak kapatılıp sistem uyursa veya internet kesilirse haber takibi çalışmaz. Kullanıcı girişinden önce 7/24 hizmet garantisi verilmez. Sistem genel uyku ayarları değiştirilmedi.

Gizli dosyalar ve VM diskleri kaynak ZIP'inden çıkarılır. Gerçek durum: reports/STATUS.json; model/output-cap/source/izolasyon raporları aynı dizinde.
