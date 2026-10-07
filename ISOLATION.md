# İzolasyon raporu

## Yapılanlar

- Referans repo GitHub API üzerinden salt okunur incelendi. Başlangıç main SHA: `e9c7c86e7577b74d26bc0d320fe6a65e05118c1b`; prompt referansıyla aynı. Son kontrolde dışarıdan gelen bir yeni commit ile main `e23969720d41e37d94222561047deb9b5a15b0c8` oldu. Salt-okunur compare incelendi: README, `src/telegram/outbox.ts` ve yeni automatic-tweet testi değişmiş; eski sisteme yeni iş ilişkisi KAP bildirimi sonrasında otomatik tweet draft kuyruğu eklenmiş. Yeni habnews bu hattı kullanmaz ve sınırlar değişmez. Karşılaştırma `reports/reference-repo-diff.json` dosyasındadır. `src/ai/prompt.ts` stil kaynağı çalışma scratch alanında okundu. Production repo içine dosya, PR, migration veya deploy yapılmadı. Yerel production checkout status kontrolü iddiası yoktur; bu oturum o checkout'u kullanmadı.
- Mevcut Hermes binary wrapper ve kaynak commit/status okundu; auth store, `.env`, credential, kişisel oturum veya anahtar içeriği **okunmadı/kopyalanmadı**. Kaynak commit `dd0e4ab81abccf7df5b11c6c16853d5e5de9db69`. Kullanıcının önceden mevcut `apps/desktop/electron/main.cjs` değişikliği başlangıç ve son kontrolde aynı kaldı. Hiçbir mevcut süreç durdurulmadı/yeniden başlatılmadı.
- Aynı revision upstream `run_agent.py` SHA256 `90c056bf5c09f12d3189ad38448d1fab74d0adf69d2b5089778d19e24a68d8ec`; yerel kaynakla aynı. Constructor AST sözleşmesi doğrulandı. `enabled_toolsets=[]`, skip_memory/context, boş fallback, credential_pool=None yolları kaynakta denetlendi. Bu gerçek import/inference testi değildir.
- Yeni dosyalar yalnız bu ayrı projectless workspace'in `outputs/heranborsa-hermes-news` ve `work` alanlarına yazıldı. Offline bağımlılıklar ayrı scratch venv'de; global Python/Hermes kurulumu değiştirilmedi.
- Mevcut hostname/service inventory read-only: macOS 27.0, çalışan Hermes GUI/Python; İlk keşifte Docker/Colima/OrbStack/Podman yoktu; kullanıcı kurulum yetkisiyle yeni Colima/Docker ve ayrı habnews Linux VM kuruldu. SSH config'in yalnız Host/HostName/User/Port yönergeleri kontrol edildi; erişilebilir Linux hedef bulunmadı, anahtarlar okunmadı. Yeni sunucu/araç/kredi satın alınmadı.

## Paket içindeki güvenlik sınırları

| Rol | Dosyalar | Ağ / yetki |
|---|---|---|
| Collector/uygulama | yalnız yeni SQLite/media/jobs, numeric recipient; bot/OAuth yok | `network_mode:none`; Unix broker üzerinden izinli HTTPS GET |
| Hermes runner | yalnız yeni auth home, bounded jobs, read-only switch; DB ve bot tokenı yok | iç ağ; proxy sadece chatgpt.com/auth.openai.com; boş LLM tool listesi |
| Approval | yalnız yeni DB/control ve yeni bot secret'ı; OAuth yok | ayrı iç ağ; proxy sadece api.telegram.org |
| Source broker | kaynak manifesti + socket + read-only switch; hiçbir credential yok | exact host allowlist, public DNS/IP pinning, her redirect yeniden kontrol, stream limit |

Read-only image, non-root UID, no-new-privileges, dropped capabilities ve bounded memory/PID çalışan container'larda uygulanıyor. Docker socket, eski repo/home, .ssh, ana Hermes/Codex config/auth, Telethon dosyası veya Her An Borsa kaynakları mount edilmez. Eski D1/R2/Worker/Pages namespace bilgileri deploy manifestinde yoktur. Runtime fetch denylist KAP/SPK alt domainlerini, Her An Borsa domainlerini, Cloudflare yönetimi ve X yayın hostlarını reddeder. Ücretli model/araç sağlayıcısı credential/config yolu bulunmaz.

**Gerçek kabul geçti:** Docker build, AIAgent import, collector/runner/approval UID 11001, role-scoped secret mounts ve doğrudan internet negatif kontrolü çalıştırıldı. Telegram/provider proxy'leri yasak hosta CONNECT 403 verdi. Squid UID/GID 13:13 olarak doğrudan foreground çalışıyor, root giriş scripti kullanılmıyor; read-only FS, cap_drop ALL, tmpfs ve PID/RAM sınırları var. Yeni VM sadece habnews runtime dizinini mount eder, kullanıcı home/SSH agent mount/forward yok. Yeni LaunchAgent ve stop/start sonrası native volume/auth korunumu doğrulandı. Host yeniden başlatılmadı. Registry digest'leri sabitlendi; imza/audit garantisi iddia edilmez.

SQLite DB yalnız `habnews.sqlite` adı ve HABN application_id ile benimsenir; eski Hermes `state.db`, `.hermes/.codex/.ssh` veya production repo path'leri reddedilir. Yabancı SQLite adı habnews olsa da marker yoksa migration çalışmaz. Audit append-only update engeli vardır; TTL silme/OS yöneticisi erişimi nedeniyle mutlak immutable değildir.

Yeni bot getMe/webhook ve özel kullanıcı callback kabulü, ayrı polling servisi ve yeni OAuth grant'i **geçti**. Mevcut grant'i ödünç alarak smoke yapılmadı. Sabit kaynak/main-text job spool'u kısa TTL ve hash kontrolü taşır; LLM'nin sonucunun DB/karar/outbox üzerinde doğrudan yazma yetkisi yoktur. Secret/token taşıyan HTTP hata URL'leri loglanmaz; runner logging kapalıdır, telemetry yerine güvenli metadata alınır.
