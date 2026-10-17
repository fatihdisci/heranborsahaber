import json,time
from habnews.collector import Collector
from habnews.live_feed import process_live_feed
from habnews.approval import Approval
from habnews.telegram import Outbox
from test_live_feed_social import source,item,FakeTelegram


def setup(db):
 a=Approval(db,123,123);s1=source();s2=s1|{'stable_id':'second','owner':'Second Publisher'}
 c=Collector(db,[s1,s2]);c.observe(s1,[]);c.observe(s2,[])
 post=item()|{'title':'TCMB politika faizine ilişkin yeni kararını açıkladı','summary':'TCMB, politika faizini yüzde 40 olarak belirledi. Kararın uygulama esasları ve ayrıntıları bankalarla paylaşıldı.'}
 return a,c,s1,s2,post


def test_duplicate_before_send_is_one_card_with_two_sources(db):
 a,c,s1,s2,post=setup(db)
 c.observe(s1,[post]);process_live_feed(db,a,[s1,s2])
 c.observe(s2,[post|{'url':'https://second.test/story'}]);process_live_feed(db,a,[s1,s2])
 rows=db.conn.execute('SELECT payload FROM habnews_outbox').fetchall()
 assert len(rows)==1
 assert 'Aynı haber · Second Publisher' in rows[0][0]
 assert db.conn.execute('SELECT count(*) FROM habnews_feed_group').fetchone()[0]==1
 assert db.conn.execute('SELECT count(*) FROM habnews_evidence').fetchone()[0]==0


def test_duplicate_after_send_edits_markup_without_new_news_message(db):
 a,c,s1,s2,post=setup(db);c.observe(s1,[post]);process_live_feed(db,a,[s1,s2])
 tg=FakeTelegram();Outbox(db,tg).send_one()
 c.observe(s2,[post|{'url':'https://second.test/story'}]);process_live_feed(db,a,[s1,s2])
 Outbox(db,tg).send_one()
 assert [x[0] for x in tg.calls]==['sendMessage','editMessageReplyMarkup']
 assert tg.calls[1][1]['message_id']==101


def test_changed_number_and_same_source_update_are_separate(db):
 a,c,s1,s2,post=setup(db);c.observe(s1,[post]);process_live_feed(db,a,[s1,s2])
 c.observe(s2,[post|{'summary':post['summary'].replace('40','45')}]);process_live_feed(db,a,[s1,s2])
 assert db.conn.execute('SELECT count(*) FROM habnews_outbox').fetchone()[0]==2
 c.observe(s1,[post|{'summary':post['summary'].replace('40','42')}]);process_live_feed(db,a,[s1,s2])
 texts=[json.loads(r[0])['text'] for r in db.conn.execute('SELECT payload FROM habnews_outbox')]
 assert 'Kaynak özeti güncellendi' in texts[-1]
 assert 'yüzde 40' in texts[-1] and 'yüzde 42' in texts[-1]


def test_short_vague_summaries_never_group(db):
 a,c,s1,s2,post=setup(db);post['summary']='Açıklama geldi.'
 for src in [s1,s2]:c.observe(src,[post]);process_live_feed(db,a,[s1,s2])
 assert db.conn.execute('SELECT count(*) FROM habnews_outbox').fetchone()[0]==2


def test_uncertain_delivery_never_suppresses_another_source(db):
 a,c,s1,s2,post=setup(db);c.observe(s1,[post]);process_live_feed(db,a,[s1,s2])
 db.conn.execute("UPDATE habnews_outbox SET status='uncertain'")
 c.observe(s2,[post]);process_live_feed(db,a,[s1,s2])
 assert db.conn.execute('SELECT count(*) FROM habnews_outbox').fetchone()[0]==2
