"""Her An Borsa topic routes: material market news, no general-news firehose."""
import json,time
import pytest
from habnews.normalizer import classify


@pytest.mark.parametrize('title',[
 'SPK haftalık bültenini yayımladı',
 'SPK manipülasyon soruşturmasında suç duyurusu yaptı',
 'Sermaye Piyasası Kurulu iki aracı kurumun yetkisini iptal etti',
 'Fon kurulu yatırımcıları koruyacak',
 'Yatırım fonlarından çıkış yavaşladı',
 'TEFAS işlem saatleri değişti',
 'Para piyasası fonlarının stopaj oranı değişti',
 'TBMM’de fon mesaisi: 455 bin yatırımcıyı ilgilendiren tasfiye düzenlemesi',
 'Borsa İstanbul’da 5 hisse üzerindeki tedbirler kalkıyor',
 'BIST 100 yüzde 6,53 geriledi',
 'Hangi hisseler temettü verecek? 36 şirketin ödeme takvimi açıklandı',
 'KAP bilanço duyurusu',
 'Yeni halka arz başvurusu onaylandı',
 'Şirketten bedelsiz sermaye artırımı kararı',
 'Yabancılar Borsa İstanbul’da 356 milyon dolarlık alım yaptı',
 'Borsa şirketinden konkordato başvurusu',
 'Aselsan yeni sözleşme imzaladı',
 'THY eylül ayı yolcu sayısını açıkladı',
 'Koç Holding yeni şirket satın aldı',
 'Akbank çeyreklik kârını açıkladı',
 'Türkiye enflasyon verisi açıklandı',
 'TCMB politika faizini indirdi',
 'TCMB zorunlu karşılık oranlarını değiştirdi',
 'Türkiye sanayi üretimi verisi açıklandı',
 'Hazine bütçe açığını açıkladı',
 'Mehmet Şimşek: Sermaye akımlarında artış bekliyoruz',
 'Türkiye’nin kredi notu yükseltildi',
 'Türkiye ile KKTC arasında ödeme sistemleri entegrasyonu güçleniyor',
 'Erdoğan: Enflasyonla mücadeleye devam edeceğiz',
])
def test_material_market_news_passes_independent_topic_routes(title):
    assert classify({'title':title})[0] in ('P0','P1')


@pytest.mark.parametrize('title',[
 'Antalya’da araç uçuruma devrildi: 2 ölü',
 'Türkiye üniversite açılışı',
 'Türkiye bilim olimpiyatlarında madalya rekoru kırdı',
 'İstanbul Boğazı’nda gemi arızası: Trafik yeniden açıldı',
 'Ankara Barosu yeni başkanını seçti',
 'Meteoroloji’den Türkiye için sağanak uyarısı',
 'Son dakika İstanbul’da deprem oldu',
 'Türkiye ve üç ülkeden ortak kınama',
 'Erdoğan’dan gençlik buluşmasına mesaj',
 'Mehmet Şimşek okul açılışına katıldı',
 'TMSF 75 personel alımı yapacak: Fon uzman yardımcısı aranıyor',
 'SPK personel alımı ilanı yayımladı',
 'İstanbul’da 250 taksi plakası için ihale',
 'Ankara’daki restorana 135 bin TL ceza',
 'Türkiye’nin fındık ihracatı 1,9 milyar doları aştı',
 'İzmir Ticaret Borsası’nda başkan değişti',
 'Dolar/TL bugün ne kadar? Güncel döviz fiyatları',
 'Dolar kaç TL oldu, Euro ne kadar?',
 'Altın fiyatları ne kadar? Gram ve çeyrek altın kaç TL?',
 'En yüksek mevduat faizi hangi bankada? Banka banka getiriler',
 'Emeklilere banka promosyonu: Maaşını taşıyana 35 bin TL',
 'Aselsan çocuklar için bilim etkinliği düzenledi',
 'THY sponsorluğunda İstanbul koşusu yapıldı',
 'Nasdaq hisseleri yükseldi',
 'ABD yatırım fonlarında yeni dönem',
 'ABD Hazine Bakanı: Washington İran stratejisini değiştirdi',
 'KAP şirket pay geri alım açıklaması',
 'Türkiye hisseleri için hedef fiyat ve al tavsiyesi',
])
def test_low_signal_and_unrelated_news_does_not_notify(title):
    assert classify({'title':title})[0] not in ('P0','P1')


def test_company_event_in_summary_can_rescue_vague_title():
    assert classify({'title':'Dev anlaşma açıklandı','summary':'Aselsan, Türkiye için yeni bir ihracat sözleşmesi imzaladı.'})[0]=='P1'


def test_economic_significance_in_summary_can_rescue_political_title():
    assert classify({'title':'Erdoğan yeni kararları açıkladı','summary':'Türkiye’de yatırım fonlarının stopaj oranı değiştirildi.'})[0]=='P1'


def test_financial_words_in_recruitment_summary_do_not_bypass_exclusion():
    assert classify({'title':'TMSF personel alımı yapacak','summary':'Tasarruf Mevduatı Sigorta Fonu; fon uzmanı, yatırım fonu ve portföy işlemleri için personel alacak.'})[0]=='filtered'


def test_large_tl_amount_is_not_a_financial_market_signal():
    assert classify({'title':'Türkiye’de 30 milyar TL uyuşturucu ele geçirildi'})[0]=='filtered'


def test_tcmb_source_does_not_bypass_topic_filter():
    assert classify({'title':'TCMB sanat yarışmasının kazananları açıklandı','source_id':'tcmb'})[0]=='filtered'


def test_turkish_uppercase_keywords_and_html_summary_remain_matchable():
    assert classify({'title':'BORSA İSTANBUL İŞLEM SAATLERİNİ DEĞİŞTİRDİ'})[0]=='P1'


def test_direct_turkey_impact_of_global_decision_is_retained():
    assert classify({'title':'Fed faiz kararı açıklandı','summary':'Türkiye’nin enflasyon ve faiz görünümüne etkisi değerlendirildi.'})[0]=='P1'


def test_pending_old_feed_card_is_refiltered_before_delivery(db):
    from habnews.db import encode
    from habnews.telegram import Outbox
    now=time.time()
    item={'title':'Türkiye üniversite açılışı','published_at':now,'first_seen_at':now,'time_precision':'second'}
    db.conn.execute('INSERT INTO habnews_observation VALUES(?,?,?,?,?,?,?,?)',('obs','test','provider','https://example.test','hash',encode(item),now,'feed_queued'))
    db.conn.execute('INSERT INTO habnews_outbox(id,recipient,part,method,payload,next_at,created) VALUES(?,?,?,?,?,?,?)',('old-card',123,0,'sendMessage',encode({'chat_id':123,'text':item['title']}),now,now))
    db.conn.execute('INSERT INTO habnews_feed_callback(nonce,observation_id,recipient,digest,outbox_id) VALUES(?,?,?,?,?)',('nonce','obs',123,'hash','old-card'))
    class NoSend:
        def call(self,*args):pytest.fail('irrelevant queued notification must not be sent')
    Outbox(db,NoSend()).send_one()
    assert db.conn.execute("SELECT status FROM habnews_outbox WHERE id='old-card'").fetchone()[0]=='filtered'


@pytest.mark.parametrize('title',[
 'Türk Telekom’a yapay zekâ ödülü verildi',
 'BIM aktüel ürün kataloğu yayımlandı',
 'Türkiye’de fonksiyonel eğitim programı başladı',
 'İstanbul’da deprem hissedilen ilçeler açıklandı',
])
def test_substrings_and_company_promotions_are_not_market_events(title):
    assert classify({'title':title})[0]=='filtered'


@pytest.mark.parametrize('title',[
 'Smart Güneş 19,5 milyon dolarlık sözleşme imzaladı',
 'Emlak Konut yeni yatırım anlaşmasını açıkladı',
 'BDDK kredi kartı limitlerine ilişkin yeni karar aldı',
 'TMSF bankaya el koydu',
 'İş Bankası’nın mevduatı yüzde 12 arttı',
])
def test_additional_listed_issuers_and_material_bank_rules(title):
    assert classify({'title':title})[0] in ('P0','P1')


@pytest.mark.parametrize('title',[
 'SPK hedef fiyat raporlarına ilişkin düzenleme yayımladı',
 'SPK hangi bankaya ceza kesti? Kurul kararları açıklandı',
 'SPK hisseyi uçuracağız diyen hesaplar için suç duyurusunda bulundu',
 'BES devlet katkısı ve emeklilik fonlarının getirileri açıklandı',
])
def test_regulator_actions_and_pension_funds_are_preserved(title):
    assert classify({'title':title})[0] in ('P0','P1')


@pytest.mark.parametrize('title',[
 'Uluslararası Para Fonu Pakistan için yatırım programını değerlendirdi',
 'Türkiye iklim fonu yeni yardım projesini açıkladı',
 'Türkiye sosyal yardım fonu ödemeleri başlıyor',
])
def test_non_investment_funds_do_not_trigger_fund_route(title):
    assert classify({'title':title})[0]=='filtered'


def test_spk_decision_is_not_excluded_because_summary_mentions_kap_buybacks():
    assert classify({'title':'SPK yeni düzenlemeyi açıkladı','summary':'KAP pay geri alım işlemleri de yeni düzenlemenin kapsamına alındı.'})[0]=='P1'


def test_official_domestic_post_still_needs_an_actual_financial_topic():
    assert classify({'title':'Enflasyonla mücadele programı devam edecek','source_id':'x-rterdogan'})[0]=='P1'
    assert classify({'title':'Gençlik buluşmasında bir araya geldik','source_id':'x-rterdogan'})[0]=='filtered'


@pytest.mark.parametrize('title',[
 'Şirketlerde sermaye kaybı hesabındaki istisna 1 Ocak 2028’e uzatıldı',
 'Merkez Bankası bir elektronik para şirketinin faaliyet iznini iptal etti',
 'TCMB bir elektronik para şirketinin faaliyet iznini iptal etti',
 'İller Bankası’nın sermayesi 250 milyar TL’ye çıkarıldı',
 'İki katılım bankası birleşiyor',
 'Ziraat Katılım ve Halk Katılım Türkiye Varlık Fonu’na devrediliyor',
])
def test_material_bank_mergers_licenses_and_capital_rules_are_not_lost(title):
    assert classify({'title':title})[0] in ('P0','P1')
