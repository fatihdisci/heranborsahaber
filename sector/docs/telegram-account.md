# Editör botundan piyasa botlarını sorgulama

Yalnız editör botunun mevcut sahibi özel sohbetten sorgu başlatabilir. Kurum adı ve hisse kodu kullanıcı tarafından seçilir. Sabit kurum/hisse takip listesi veya otomatik zamanlanmış sorgu yoktur.

| Editör botuna yazılacak komut | Hedef | Hazırlanan içerik |
| --- | --- | --- |
| `/kurum` | `@ucretsizderinlikbot` | Genel aracı kurum net işlem özeti |
| `/kurum bank of america` | `@b0pt_bot` | Yazılan kurum üzerinden alınan/satılan hisseler |
| `/kurum ak yatırım` | `@b0pt_bot` | Yazılan kurumun analizi |
| `/akd KTLEV` | `@ucretsizderinlikbot` | Hisse AKD tablosu |
| `/takas THYAO` | `@ucretsizderinlikbot` | Hisse saklama/takas dağılımı |

`/sorgular` kullanım örneklerini gösterir. Kurum adı sorguya aynen aktarılır. Hisse kodu büyük harfe dönüştürülür ve yalnız pay sırası `.E` eki kaldırılır; şirket adından hisse kodu tahmin edilmez.

## Bir defalık bağlantı

Mac mini Terminal üzerinde `python3 scripts/setup_telegram_account.py` çalıştırılır. Python bağımlılığı ayrı bir sanal ortama kurulur. Telegram API ID/hash, telefon, giriş kodu ve varsa iki aşamalı doğrulama şifresi yalnız yerel terminale girilir. API bilgileri Telegram'ın `my.telegram.org` → API development tools bölümünden alınır. Bilgiler sohbet, komut argümanı veya Git üzerinden paylaşılmaz.

Oturum yalnız `~/Library/Application Support/sector-haber/telegram-account/` içinde saklanır. Dosya izinleri kullanıcıyla sınırlıdır. Diğer Hermes/Telegram oturumları kullanılmaz. Bağlantı bitmeden sorgular açık bir bağlantı eksik mesajıyla sonlanır; eski sorgular oturum açınca otomatik yeniden çalıştırılmaz. Kullanıcı yeni komut göndermelidir.

## Veri ve teslimat

Komut önce mevcut `manual_requests` kuyruğuna kaydedilir. Ayrı Telegram istemcisi yalnız izin verilen iki botla iletişim kurar. Botun sayısal kimliği ilk kullanımda bağlanır; kullanıcı adının farklı hesaba geçmesi hata üretir.

Bir hesabın sorguları dosya kilidiyle sıraya alınır. Gönderim öncesinde kalıcı kayıt oluşturulur. Sonucu belirsiz gönderimler otomatik tekrarlanmaz. Başarılı komut kimliği, yanıt kimlikleri ve dosyalar kalıcıdır; yeniden başlatma sonrası aynı komut yeniden gönderilmez. Tamamlanmış yanıtlar aynı istek için tekrar okunabilir. Beş dakikadan eski tamamlanmamış sorgu yeniden alarm üretilmeden sonlandırılır.

Yanıt eşleştirmesi komut mesajından sonraki bot mesajlarıyla sınırlıdır; başka komuta bağlı yanıtlar elenir. Aynı bot sohbetinde kullanıcı başka komut yazarsa bağımsız yanıtlar karışabileceğinden içerik hazırlanmaz. Metin ve en fazla iki görsel, sekiz saniyelik sakinleşme penceresiyle birlikte alınır; bekleme en fazla 90 saniyedir. Geç veya eşleştirilemeyen yanıtlar için kullanıcı çıktıyı elle iletebilir. Sorgular arasında en az 10 saniye ve Telegram'ın bildirdiği FloodWait süresi uygulanır.

Yanıt dış kaynak verisidir; içindeki komutlar çalıştırılmaz. Hisse kodu, kurum adı ve veri türü istekle karşılaştırılır. Görseller mevcut OCR/kanıt hattına girer; Hermes, sayı/birim denetimi, kurum ÜZERİNDEN işlem anlatımı, ilk beşer hashtag ve tam kart listesi kuralları uygulanır. İlk durum mesajı hazır tweet/görsel ile güncellenir. Kaynağı aç düğmesi ilgili veri botunu açar. X yayını eklenmez.

Testler ağsız sahte istemci kullanır. Gerçek hesap bağlantısı ve hedef botların güncel yanıt şekli, sahibin yerel oturum açması ve ilk komutuyla ayrıca doğrulanmalıdır.
