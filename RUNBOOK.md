# Kurulum ve işletim

## Bu makinedeki durum

Erişilen host macOS 27.0, ARM64. Yeni Colima `habnews` Linux VM, Docker ve altı ayrı container kuruldu. Gerçek AIAgent import, özel OAuth/model/catalog/output-cap ve rol izolasyonu geçti. Çalışan instance `/Users/fatihdisci/Library/Application Support/habnews` içindedir. Bot `@habernewssbot`, yalnız numeric özel kullanıcıya bağlıdır. Mevcut Hermes/Her An Borsa servisleri veya auth/config değiştirilmedi. Yeni sunucu/abonelik alınmadı.

Mac işletimi ve mevcut aktivasyon durumu için **[MACOS.md](MACOS.md)** kullanın. Aşağıdaki Linux/systemd komutları alternatif dağıtım içindir; bu Mac'te systemd installer çalıştırılmadı.

## 1. Ayrı dizin ve servis

Paketi Linux hosta aktarın. Paket içindeki `.env.example` sadece placeholder'dır. Hiçbir eski `.env`, OAuth auth store, Codex/Hermes home, Telegram/Telethon oturumu veya SSH key'i kopyalamayın.

```bash
sudo bash deploy/install-linux.sh
cd /opt/habnews
docker compose -f deploy/compose.yaml build
```

Installer yalnız yeni OS kullanıcısı `heranborsa-hermes-news` (UID 11001), `/opt/habnews`, `/var/lib/habnews` ve aynı isimli systemd unit'i oluşturur. Hedef/UID zaten varsa overwrite/adoption yapmadan durur. Servisi enable/start etmez. Hostta çalışan başka Hermes için install/update yapılmaz. Build yalnız yeni image içinde sabit Hermes revision'u ve upstream `uv.lock` kullanır. Docker daemon kurulmaz/yeniden başlatılmaz.

## 2. Yeni Telegram botu, gizli yerel giriş

Telegram BotFather'da **yeni** bot oluşturun ve kendi özel sohbetinizde `/start` gönderin. Eski Her An Borsa tokenını kullanmayın. Tokenı bu sohbete veya shell argümanına yapıştırmayın.

Yeni app interpreter'ında:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/python -m habnews.cli configure-telegram --directory private
sudo chown -R 11001:11001 private
```

Komut tokenı `getpass` ile alır, `getMe` bot ID'sini kontrol eder ve ayrı bot olduğunu operatöre kaydettirir. `getWebhookInfo` doluysa değiştirmeden durur. `private/telegram.json` 0600, `private/recipient.json` yalnız numeric user/chat ID'lerini taşır. İkincisi collector'a, token yalnız approval rolüne mount edilir. Bu komut mevcut bot komut/webhook'unu değiştirmez. Username'e güvenmez. Private chat ve allowed user ID'lerini doğru girin; bot mesaj gönderimi yalnız pozitif private ID'ye yapılır.

`getUpdates` tek sahibi approval servisidir; OS file lock ikinci yerel approval sürecini engeller. Başka hosttaki polling sahibini Telegram 409 ile fark eder; tüm dünyada başka polling sahibi yok diye kesin bir iddia kurulmaz. Bu bot için Hermes gateway açmayın.

## 3. Yeni habnews OAuth grant'i

Yeni provider proxy'yi başlatın; yeni runner yalnız iç ağa ve provider proxy'ye erişir.

```bash
docker compose -f deploy/compose.yaml up -d provider-egress
docker compose -f deploy/compose.yaml run --rm runner login
```

Hermes'in sabitlenen sürümündeki resmi `_login_openai_codex(..., force_new_login=True)` device-code akışı kullanılır. CLI/private helper sürüme kilitlidir; farklı revision'da sözleşme yeniden denetlenmelidir. Kullanıcı cihaz girişini aynı ChatGPT Pro hesabıyla tamamlar. Auth `/auth/habnews` içinde kalır. Boş OS home ve `CODEX_HOME` sayesinde dış credential otomatik import'u göremez. Eski auth mount edilmez; logout/revoke/refresh yapılmaz. Yenileme resmi Hermes auth resolver'ına aittir. Bu komutun çıktısını toplu log/sohbet arşivine kopyalamayın; device code kullanıcı giriş verisidir.

```bash
docker compose -f deploy/compose.yaml run --rm runner smoke
```

Smoke önce gerçek hesap katalogunu sorgular; synthetic forward-compat model eklemesini kullanmaz. Katalogda **tam `gpt-6.1-sol`** bulunmazsa durur. `low` ve `medium` ile iki açık sentetik `TEST_OK` isteği yapılır; normal hızla daha kısa süre veren destekli reasoning seçilir. Model/provider/transport/request/run metadata'sı kaydedilir. AIAgent server-effective-model veya request ID bildirmiyorsa alan `null`, sınır açık yazılır; istek modeliyle sunucu kimliği karıştırılmaz. Dosya `state/jobs/model-smoke.json`.

Backend output-token override'ının desteklendiğini ayrıca gerçek taşıma üzerinde doğrulayın. Bu Hermes sürümünün standart Codex cap davranışı sınırlıdır; adapter `max_output_tokens` override'ı reddedilirse fallback yok, kapalı kalın. `output_cap_verified` ve `live_acceptance_verified` eksikken `/haber_baslat` çalışmaz. Görünmeyen reasoning tüketimi ve hesabın gerçek toplam kotası uydurulmaz.

## 4. Kaynak kabulü

`sources.yaml` içindeki her kaynak için endpoint, redirect hostları, ownership, `parser_version`, zaman, robots/terms, kısa kanıt retention izni ve doğrulama raporunu inceleyin. `verified_at`, `terms_approved`, `validation_report`, `health=validated` tamamlanmadan `enabled=true` kabul edilmez. Resmî domain olmak görsel yeniden kullanım lisansı değildir.

- RSS için gerçek makale parser'ını da test edin; feed erişimi makale erişimi demek değildir.
- TCMB `tcmb_home` ana sayfadaki sınırlı duyuru kartlarını okur. JS yıl arşivi/eksiksiz basın geçmişi taraması vaat etmez.
- HMB/BIST/TÜİK/Resmî Gazete discovery kayıtları kapalı; endpoint/parser doğrulanmadan enable etmeyin.
- Investing makale örneği 403, BDDK TLS başarısız: aşmayın, kapalı tutun.
- KAP/SPK kaynağı/adaptörü eklemeyin; medya tekrarları conservative scope filtresindedir.

```bash
.venv/bin/python -m habnews.cli validate-sources
```

Bu komut az sayıda salt-okunur doğrulama içindir; periyodik scheduler değildir. Canlı supervisor'la paralel sürekli polling başlatmayın.

## 5. İzolasyon ve canlı kabul

```bash
docker compose -f deploy/compose.yaml run --rm --entrypoint python collector /app/verify-container.py collector
docker compose -f deploy/compose.yaml run --rm --entrypoint /opt/hermes/.venv/bin/python runner /app/verify-container.py runner
docker compose -f deploy/compose.yaml run --rm --entrypoint python approval /app/verify-container.py approval
```

UID, gizli dosya görünürlüğü, mount ve doğrudan internetin kapalı olduğu test edilir. Hedefte provider/Telegram proxy negatif-host kontrolü ve Squid boot doğrulaması ayrıca gereklidir. Collector socket broker'ı yalnız enabled allowlist HTTPS kaynaklarını okur; yeniden DNS/IP kontrolü, IP pinning ve TLS SNI kullanır. LLM shell/browser/tool listesi boş kalmalıdır.

Yeni approval servisini başlatın; ingest/LLM halen kapalıdır:

```bash
docker compose -f deploy/compose.yaml up -d telegram-egress approval
```

Açık operatör testi için, haber servisi halen kapalıyken şu komutu çalıştırın:

```bash
docker compose -f deploy/compose.yaml run --rm --entrypoint python approval /app/send-labelled-test.py
```

Etiketli TEST/SENTETİK paket yalnız sahibine gider. Mevcut approval polling servisi kart onayını sürüm/hash/private-user kontrolüyle işler. Başarılı onay `live_acceptance_verified=true` kaydeder. Test gerçek model çağrısı değildir. Callback/private-chat/sürüm akışını hedefte doğrulayın. `reports/DRY_RUN.json` içerik örneğidir; gerçek OAuth testi değildir. Model smoke başarılı olsa bile bunu otomatik canlı haber gibi göndermeyin. Kurulu Mac instance'ında bu interactive callback kabulü yapıldı; alternatif yeni Linux hedefte ayrıca yapılmalıdır.

```bash
docker compose -f deploy/compose.yaml run --rm --entrypoint python collector /app/record-readiness.py
```

Bu operatör kabulü kayıt eder; kendi başına fetch/model işlemini açmaz. Bot, kaynak, model, output cap ve izolasyon gerçek kontrol edilmeden bu attestasyonu vermeyin.

```bash
docker compose -f deploy/compose.yaml up -d
# Son adım: özel Telegram sohbetinde /haber_baslat
sudo systemctl enable heranborsa-hermes-news
```

Compose restart policy bağımsız süreklilik sağlar; Codex kapansa da host açıkken çalışabilir. Host uyurken/kapalıyken takip yoktur. Startup `enabled=false` değerini kendiliğinden `true` yapmaz.

## 6. İşletim ve durdurma

Özel Telegram komutları: `/haber_durum`, `/haber_durdur`, `/haber_baslat`, `/haber_butce`, `/haber_kaynaklar`, `/haber_taslak <tam-draft-id>`.

Telegram erişilemiyorsa:

```bash
cd /opt/habnews
docker compose -f deploy/compose.yaml exec collector python -m habnews.cli --db /data/habnews.sqlite stop
docker compose -f deploy/compose.yaml stop
```

Local kill switch commit'i `/control/runtime-state.json` üzerinden runner/source broker'a da yayılır. Başlamış dış çağrı geri alınamaz; stop sonrası sonucu yeni paket olarak yollama engellenir. Sadece kuyruk ve onay/admin durumu korunur. Mevcut Hermes veya Her An Borsa servislerini bu komutlarla durdurmayın.

`health`/`status` CLI private durum çıktısı ve Docker healthcheck supervisor'ı vardır. Açık HTTP durum portu yoktur. Telegram/host bozulduğunda aynı kanaldan alarm garantisi yoktur. Günlük zorunlu özet gönderilmez.

## 7. Belirsiz teslimat ve manuel paylaşım

Telegram API kabulü sonrası makbuz yazılamazsa `uncertain`; otomatik tekrar yok. Photo/text/metadata part sırası korunur; ön part belirsizse sonrakiler bekler. 429 bot genelinde kalıcı cooldown, kaynak retry bağımsız. Kullanıcı gerçekten almadığını doğruladığında:

```bash
docker compose -f deploy/compose.yaml exec collector python -m habnews.cli --db /data/habnews.sqlite reconcile-delivery OUTBOX_ID --not-received --reason 'Sahibi özel sohbeti kontrol etti; mesaj ulaşmadı'
```

Yeniden gönderim audit edilir ve gönderim öncesinde tazelik tekrar denetlenir. Onaylı paket dışa aktarımı:

```bash
docker compose -f deploy/compose.yaml exec collector python -m habnews.cli --db /data/habnews.sqlite export-approved DRAFT_ID /data/approved/PAKET_ADI
```

`draft.txt`, `metadata.json`, hakları uygunsa orijinal görsel ve `attribution.txt` oluşur. Özel Telegram kaynak önizlemesi (`private_source_preview`, hak durumu `unknown`) fotoğraf olarak yeniden yayınlama paketine eklenmez; kaynak bağlantısı ve gerekçe `attribution.txt` içinde kalır. Eski/değiştirilmiş onay export edilmez. CC-BY/CC-BY-SA şartlarını paylaşırken koruyun. Paylaşım insan tarafından elle yapılır.

## 8. Backup, restore ve geri alma

```bash
docker compose -f deploy/compose.yaml exec collector python -m habnews.cli --db /data/habnews.sqlite backup /data/backups/YENI_TARIH --media /data/media
# Restore daima boş hedefe; enabled=false açılır.
python -m habnews.cli restore BACKUP_DIZINI BOS_HEDEF_DIZIN
```

Backup SQLite online backup + private medya hash manifesti içerir; OAuth, bot secret'ı ve geçici tam kaynak/job spool'u içermez. Restore integrity testinin offline fixture kontrolü yapıldı. Gerçek host backup politikası ve harici yedek diski operatöre bağlıdır.

Geri alma: önce `stop`, sonra sadece `heranborsa-hermes-news` unit'ini disable/stop ve `docker compose -f /opt/habnews/deploy/compose.yaml down` kullanın. `docker system prune`, genel service kill veya eski grant revoke yok. Yalnız habnews dosyalarını, kendi yedeğiniz/kararlarınız korunarak kaldırın. Yeni OAuth grant'i kaldırılacaksa sadece yeni giriş üzerinden kullanıcı yönetsin; eski oturumlara dokunulmaz.
