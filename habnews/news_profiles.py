"""Editorial priorities inferred from source text; never a source of new facts."""
import re

PROFILES = [
    ('fund_liquidation', r'tasfiye.*fon|fon.*tasfiye',
     'Fon tasfiyesinde açıklamayı yapan portföy şirketini açıkça belirt. Toplam tasfiye edilen fon sayısı ve toplam büyüklük ile bugün tasfiye edilen fonlar, bugünkü büyüklük ve yatırımcı sayısını ayrı tut; farklı grupların sayılarını birleştirme. Şirketin “fonumuz/fonlarımız” sözlerini botun kendi sözü gibi yazma. Kendi başına anlaşılır kaynak cümleleri seç; “Bununla birlikte” diye bağlamsız başlama. Kaynak alıntısında konuşanı açıkça belirt.'),
    ('claim', r'iddia|yalanla|soruşturma|suçlama',
     'İddia veya yalanlamayı kimin yaptığını ilk cümlede belirt. İddiayı gerçekleşmiş olay gibi yazma; yalanlama ve soruşturma aşamasını koru.'),
    ('rate', r'politika faizi|faiz kararı|para politikası kurulu',
     'Kararı alan kurum, yeni faiz oranı ve kararın yönünü öne çıkar. Önceki oran ve yürürlük tarihi yalnız kaynakta varsa kullan. Beklentiyi karar gibi sunma; baz puan farkını kendin hesaplama.'),
    ('inflation', r'enflasyon|tüfe|üfe',
     'Verinin dönemini ve aylık/yıllık ayrımını rakamla birlikte ver. Beklenti ile gerçekleşmeyi ayır. Bir önceki dönemin rakamını yeni veri gibi sunma.'),
    ('current_account', r'cari açık|cari açığ|cari fazla|cari denge|ödemeler dengesi',
     'Aylık cari fazla/açık ile yıllıklandırılmış cari dengeyi ayrı ve dönemleri açık yaz. Farklı dönemlerin tutarlarını birbirinin yerine kullanma.'),
    ('earnings', r'net k[âa]r|net zarar|bilanço|hasılat|finansal sonuç',
     'Şirketi, hesap dönemini ve asıl finansal sonucu öne çıkar. Net kâr, faaliyet kârı ve hasılat farklı kalemlerdir; nominal/reel ayrımını koru. Karşılaştırma yalnız kaynakta varsa ekle.'),
    ('dividend', r'temettü|k[âa]r payı',
     'Şirket, pay başına brüt/net tutar, ödeme tarihi ve teklif/onay aşamasını ayır. Genel kurul onayı bekleniyorsa kesin ödeme gibi yazma; temettü verimi hesaplama.'),
    ('company', r'sözleşme|yatırım|birleşme|satın alma|ihale',
     'Şirket, somut gelişme, tutar/para birimi ve gerekli izin/koşulu öne çıkar. Plan, teklif, imza ve tamamlanma farklı aşamalardır; şirket adı yerine belirsiz özne kullanma.'),
]
DEFAULT = ('general', 'Kim, ne yaptı, hangi dönemde ve hangi koşulla sorularını kaynakta bulunan bilgilerle yanıtla. Ayrıntı yalnız ana gelişmeyi anlamayı kolaylaştırıyorsa ekle.')


def profile(text):
    for name, pattern, guidance in PROFILES:
        if re.search(pattern, text, re.I):
            return {'type': name, 'guidance': guidance}
    return {'type': DEFAULT[0], 'guidance': DEFAULT[1]}


def profile_prompt(text):
    selected = profile(text)
    return '\nHABER TÜRÜNE GÖRE ÖNCELİK\n' + selected['guidance'] + '\nBu alanlar eksikse bilgi uydurma; yalnız mevcut kaynak olgularını seç.\n'
