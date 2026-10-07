# GPT’ye aktar

Haber kartında Haberi aç → Tweet oluştur → **GPT’ye aktar** bulunur. Son düğme model çağrısı yapmaz; aynı kaynak okuyucusuyla seçilen haberin başlığını ve gövdesini yeniden alır. Botta kullanılan ortak editoryal promptu bu tam metnin üzerine koyar. Dış sohbet sürümü JSON yerine yalnız tweet ister; başlık başında emoji, 2–3 ilgili hashtag ve 380 karakter sınırı uygular.

Telegram'ın yerleşik CopyTextButton alanı yalnız 256 karakter kabul eder. Bu yüzden tam metin o alana sıkıştırılmaz. Bot görseli gerçek fotoğraf olarak gönderir; mesajın **Prompt + haberi kopyala** düğmesi küçük bir HTTPS ekranı açar. Ekrandaki **Kopyala** bütün prompt ve haberi tek işlemle panoya alır. Telefon panosuna yazmak için bu kullanıcı dokunuşu gereklidir. GPT'de bir sohbete yapıştırıldığında yalnız tweet taslağı istenir. Fotoğrafı GPT'ye ayrıca eklemek istersen Telegram'dan kaydedebilirsin; metin panosuna görsel eklenmez.

Kopyalama ekranı: https://fatihdisci.github.io/heranborsahaber/gpt/

Haber metni gzip/base64url ile URL'nin `#` fragment bölümünde taşınır; GitHub Pages sunucusuna gönderilmez. Sayfa harici script, analytics, fetch veya storage kullanmaz; SHA-256 ve karakter sayısını doğrular, açıldıktan sonra fragmenti tarayıcı geçmişinden çıkarır. Metni HTML olarak çalıştırmaz. Sayfanın kodu public, haber başına bir public dosya veya veri tabanı yoktur. Telegram mesajındaki bağlantıya sahip biri içeriği okuyabilir.

Haber veya bağlantı çok uzunsa, ya da Telegram uzun bağlantıyı reddederse, prompt + tam haber kesilmeden UTF-8 TXT dosyası olarak gönderilir. Kaynak gövdesi okunamazsa RSS özeti tam haber diye aktarılmaz. Sosyal hesaplarda kaynak okuyucunun doğruladığı tam sahipli paylaşım kullanılır; sistemde bir fotoğraf bulunmuyorsa yalnız aktarım metni gelir.

Callback kullanıcı, özel sohbet, kaynak kartının mesaj ID'si ve haber digest'iyle bağlıdır; Tweet oluştur düğmesinin durumunu veya model bütçesini değiştirmez. Kaynak görselleri mevcut özel önizleme hak statüsünü korur. Geçici aktarım payload'ları 24 saat sonra periyodik temizliğe alınır. Dış sohbet sonucu botun JSON/kanıt doğrulayıcısından geçmez.

Doğrulama: `tests/test_gpt_export.py`, `reports/tests.xml`, `reports/GPT_EXPORT_AUDIT.json`.
