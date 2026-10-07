Güncelleme: Canlı kaynak kartları ve isteğe bağlı Tweet oluştur akışı kuruldu. Aşağıdaki rapor önceki teyit bekleyen bildirim yapısını anlatır; güncel davranış [LIVE_FEED.md](LIVE_FEED.md) içindedir.

# Foreks ve Bloomberg HT geçiş incelemesi

Kontrol: 2026-10-06T14:38:02.996071+00:00. Referans revizyon: `40e7b437f46cb53f348c76e4f99a718b3b61d4d2`. Eski repo ve servisler değiştirilmedi.

| Kaynak | Eski yapı | Yeni canlı yapı | Sonuç |
|---|---|---|---|
| Foreks | /rss, dakikada bir | Aynı /rss, dakikada bir | Kaynak erişimi aynı |
| Bloomberg HT | /rss, dakikada bir | /rss/tum-haberler.xml, dakikada bir | Eski adres yenisine yönleniyor; 50/50 haber bağlantısı aynı |

Matriks güncel tek dal olan main içinde bulunmadı. Kullanıcı Matriks gereksinimini kaldırdı.

Kaynak erişimi eşdeğer; bildirim davranışı ve kapsam henüz eşdeğer değil. Eski servis ilgili RSS başlığını/özetini doğrudan Telegram'a yollar. Yeni servis ana metni okur, resmî birincil kaynak veya iki bağımsız kaynak ailesiyle teyit bekler; doğrulanan taslağı kullanıcı onayına sunar. Yeni servisin KAP/SPK ve Türkiye bağlantısı filtreleri eski şirket haberlerinin bir bölümünü eleyebilir. Genel olaylarda farklı başlıklar otomatik birleşmeyebilir; bu da teyit beklemeye neden olabilir. Mac açık ve çevrimiçi olmalıdır. Eski Worker bu Mac'ten bağımsızdır.

Bu nedenle eski kaynakları henüz kapatmadım. KAP/SPK hattı zaten bu yeni sistemin kapsamı dışındadır ve mevcut sistemde sürmelidir. Eski bildirimlerden aynı kapsamda yeni taslak teslimatı ölçülmeden tam ikame doğrulanmış sayılamaz.

Yalnız yeni habnews collector yeniden oluşturuldu. Foreks/Bloomberg HT canlı yapılandırması 60 saniye; iki kaynağın baseline kayıtları korundu; LLM ready ve açık olay sayısı sıfır. Yeni test eklenmedi: yapılandırma değişikliği gerçek çalışan container içinden doğrulandı. Önceki 130 test sonucu geçerlidir.

Referans kod: [kaynaklar](https://github.com/fatihdisci/heranborsacode/blob/40e7b437f46cb53f348c76e4f99a718b3b61d4d2/src/rss/sources.ts), [RSS hattı](https://github.com/fatihdisci/heranborsacode/blob/40e7b437f46cb53f348c76e4f99a718b3b61d4d2/src/rss/poll.ts), [filtre](https://github.com/fatihdisci/heranborsacode/blob/40e7b437f46cb53f348c76e4f99a718b3b61d4d2/src/rss/filter.ts), [zamanlama](https://github.com/fatihdisci/heranborsacode/blob/40e7b437f46cb53f348c76e4f99a718b3b61d4d2/src/scheduler/shards.ts).
