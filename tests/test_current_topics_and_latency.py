import json,time
import pytest
from habnews.normalizer import classify
from habnews.article import extract_document
from habnews.collector import Collector
from habnews.source_content import extraction_failure_code
from habnews.editorial_prompt import clipboard_prompt,model_policy
from habnews.news_profiles import profile

@pytest.mark.parametrize('title',[
 'MSCI kararı, fon krizi ve Avrupa riski: Piyasaları ne bekliyor?',
 'Fon krizinde takas kesinliği tartışması büyüyor',
 'PBLK kayıtları ve yatırımcı alacakları için yeni açıklama',
 'MKK PBLK blokaj kayıtları konusunda açıklama yaptı',
 'Takas kesinliği düzenlemesi komisyonda kabul edildi',
 'Muaccel alacaklı yatırımcılar için ödeme takvimi açıklandı',
 'Yatırımcı tazmin düzenlemesi için kanun teklifi verildi',
 'Fonlarımızın tasfiye işlemleri tamamlandı',
 'Orzax hisselerinde tasfiye kaynaklı satışlar sona erdi',
 'Borsa İstanbul’da şirketlerin bilanço takvimi açıklandı',
 'Sermaye Piyasası Kurulu yatırım fonları için karar aldı',
 'ABD piyasalarında düşüş: Türkiye fon krizi tartışılıyor',
])
def test_current_topics_and_existing_market_routes_pass(title):
 assert classify({'title':title})[0] in ('P0','P1')

@pytest.mark.parametrize('title',[
 'PBLK adlı oyun için yeni güncelleme çıktı',
 'ABD yatırım fonlarında kriz büyüyor',
 'Avrupa yatırım fonları kriz nedeniyle tasfiye ediliyor',
 'İstanbul’da araç takas festivali düzenlendi',
 'Banka banka en yüksek mevduat faizleri',
 'TMSF fon uzman yardımcısı personel alımı ilanı',
 'Türkiye’de futbol kulübü yeni formasını tanıttı',
])
def test_new_focus_does_not_turn_into_a_general_news_route(title):
 assert classify({'title':title})[0] not in ('P0','P1')

def test_liquidation_sale_survives_routine_kap_exception():
 assert classify({'title':'Orzax hisselerinde tasfiye kaynaklı satışlar sona erdi',
                  'summary':'Şirket KAP pay satış işlemleri hakkında açıklama yaptı.'})[0]=='P0'
 assert classify({'title':'KAP pay geri alım işlemleri açıklandı'})[0]=='scope_excluded'

def test_new_prompt_keeps_legal_stages_and_code_interpretation_source_bound():
 doc={'title':'PBLK ve takas kesinliği','body':'Yatırımcı alacaklarına ilişkin kanun teklifi komisyondan geçti.','source_url':'https://fixture.invalid/topic'}
 assert profile(doc['title'])['type']=='investor_settlement'
 for prompt in (clipboard_prompt(doc,{'owner':'TEST'}),model_policy({'manual_attribution':True,'source_title':doc['title']})):
  assert 'otomatik ödeme' in prompt and 'Genel Kurul' in prompt
  assert 'hukuki sonuç çıkarma' in prompt and 'fiilen ödenen tutar' in prompt

def sources():
 return [{'stable_id':str(i),'enabled':True,'method':'rss','endpoint':'https://fixture.invalid/'+str(i),
          'allowed_hosts':['fixture.invalid'],'polling_interval':60,'source_family':str(i),'priority':'B'} for i in range(5)]

def test_poll_batch_limit_bounds_network_work_without_starving_sources(db,monkeypatch):
 calls=[]
 def get(self,url,headers):
  calls.append(url);return b'<rss><channel/></rss>',{'content-type':'application/rss+xml'},url,200
 monkeypatch.setattr('habnews.collector.Fetcher.get',get)
 collector=Collector(db,sources())
 collector.poll(max_sources=2);assert len(calls)==2
 collector.poll(max_sources=2);assert len(calls)==4
 collector.poll(max_sources=2);assert len(calls)==5
 assert len(set(calls))==5

def test_failed_source_still_leaves_room_for_other_sources(db,monkeypatch):
 calls=[]
 def get(self,url,headers):
  calls.append(url)
  if url.endswith('/0'):raise TimeoutError()
  return b'<rss><channel/></rss>',{'content-type':'application/rss+xml'},url,200
 monkeypatch.setattr('habnews.collector.Fetcher.get',get)
 collector=Collector(db,sources());collector.poll(max_sources=2)
 assert len(calls)==2
 collector.poll(max_sources=2)
 assert len(calls)==4 and calls[2].endswith('/2')
 assert db.conn.execute("SELECT health FROM habnews_source WHERE id='0'").fetchone()[0]=='degraded'

def test_feed_batch_drains_backlog_without_waiting_for_each_network_cycle(db):
 from habnews.live_feed import drain_live_feed
 from habnews.approval import Approval
 source=sources()[0]|{'delivery_mode':'live_feed','owner':'TEST'}
 c=Collector(db,[source]);c.observe(source,[])
 now=time.time()
 c.observe(source,[dict(title=f'BIST hisse {i} temettü kararı',summary='',source_id='0',provider_id=str(i),
   url=f'https://fixture.invalid/story/{i}',published_at=now,time_precision='second') for i in range(25)])
 assert drain_live_feed(db,Approval(db,123,123),[source])==20
 assert db.conn.execute("SELECT count(*) FROM habnews_queue WHERE kind='live_feed' AND status='pending'").fetchone()[0]==5
 assert drain_live_feed(db,Approval(db,123,123),[source])==5

@pytest.mark.parametrize('linked',[lambda u:u,lambda u:{'@id':u}])
def test_structured_body_identity_and_table_rows_are_preserved(linked):
 url='https://fixture.invalid/story'
 body='<p>Şirketlerin yatırım kararları koşullara tabidir. İzinler henüz tamamlanmadı.</p><table><tr><th>Şirket</th><th>Tutar</th></tr><tr><td>A Şirketi</td><td>10 milyon TL</td></tr><tr><td>B Şirketi</td><td>20 milyon TL</td></tr></table><p>Her şirket için izin alınması koşulu korunur.</p>'
 html='<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','headline':'Yatırım kararları','mainEntityOfPage':linked(url),'articleBody':body})+'</script>'
 d=extract_document(html.encode(),'text/html',url)
 assert 'A Şirketi | 10 milyon TL\nB Şirketi | 20 milyon TL' in d['body']
 assert 'İzinler henüz tamamlanmadı.' in d['body'] and 'izin alınması koşulu' in d['body']

def test_structured_body_cannot_read_a_different_main_entity():
 html='<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','mainEntityOfPage':{'@id':'https://fixture.invalid/wrong'},'articleBody':'Farklı haberin metni. '*20})+'</script>'
 with pytest.raises(ValueError,match='main_text_missing'):extract_document(html.encode(),'text/html','https://fixture.invalid/selected')

def test_parser_error_audit_never_includes_article_text_or_url():
 assert extraction_failure_code(ValueError('cnbce_gallery_incomplete'))=='cnbce_gallery_incomplete'
 assert extraction_failure_code(ValueError('https://private.example/article?token=secret'))=='ValueError'

@pytest.mark.parametrize('word',['hisselerde','hisselerinde','hisselerinin','hisselerindeki','hisselerden','hisselerinden','hissesinin'])
def test_stock_suffixes_do_not_drop_issuer_events(word):
 assert classify({'title':f'Örnek şirket {word} yeni satış açıklaması yaptı'})[0] in ('P0','P1')

@pytest.mark.parametrize('enabled,timeout',[(True,5),(False,20)])
def test_idle_telegram_polling_bounds_notification_wait(db,enabled,timeout):
 from habnews.telegram import ApprovalService
 from habnews.approval import Approval
 db.set_state('enabled','true' if enabled else 'false')
 seen=[]
 class Fake:
  def call(self,method,payload):
   assert method=='getUpdates';seen.append(payload);return []
 ApprovalService(db,Approval(db,123,123),Fake(),123).tick()
 assert seen[0]['timeout']==timeout

def test_shared_reader_keeps_structured_rows_for_tweet_and_gpt_export(monkeypatch):
 from habnews.source_content import read_document,document_text
 body='<p>Yatırım kararları izinlere tabidir ve henüz kesinleşmemiştir.</p><table><tr><td>A Şirketi</td><td>10 milyon TL</td></tr><tr><td>B Şirketi</td><td>20 milyon TL</td></tr></table><p>Onay alınmadan uygulamaya geçilmeyecek.</p>'
 html='<script type="application/ld+json">'+json.dumps({'@type':'NewsArticle','url':'https://fixture.invalid/story','headline':'Şirketlerin yatırım kararları','articleBody':body})+'</script>'
 monkeypatch.setattr('habnews.source_content.Fetcher.get',lambda *a,**k:(html.encode(),{'content-type':'text/html'},'https://fixture.invalid/story',200))
 doc=read_document({'url':'https://fixture.invalid/story','title':'Şirketlerin yatırım kararları'},{'enabled':True,'allowed_hosts':['fixture.invalid']},lambda:None)
 data=json.loads(clipboard_prompt(doc,{'owner':'TEST'}).split('HABER VERİSİ\n')[1])
 assert data['haber_metni']==doc['body'] and data['haber_metni'] in document_text(doc,{})
 assert 'A Şirketi | 10 milyon TL\nB Şirketi | 20 milyon TL' in data['haber_metni']

@pytest.mark.parametrize('title',[
 'Anthropic, şirket hisselerinin yüzde 5’ini kamu yararına kullanacak',
 'JPMorgan’dan Bitcoin tahmini: Altın ve hisseleri geride bırakabilir',
 'Elon Musk’ın uçan otomobil gösterisi yetmedi: Tesla hisseleri düşüşte',
 'Nvidia hisselerinde sert yükseliş',
])
def test_foreign_issuers_do_not_leak_through_expanded_stock_suffixes(title):
 assert classify({'title':title})[0]=='filtered'
 assert classify({'title':title,'summary':'Türkiye BIST yatırımcıları üzerindeki etkisi ele alındı.'})[0] in ('P0','P1')

def test_current_topic_tags_describe_the_validated_text():
 from habnews.tweet_style import decorate
 text='MKK PBLK kayıtları ve takas kesinliği konusunda yatırımcı alacaklarına ilişkin açıklama yaptı.'
 styled=decorate(text,text)
 assert '#PBLK' in styled and '#takas' in styled
 assert '#gündem' not in styled and '#haber' not in styled

def test_source_command_reports_failed_access_and_exact_poll_cadence(db,monkeypatch):
 from habnews.telegram import ApprovalService
 from habnews.approval import Approval
 src=sources()[0]|{'polling_interval':90,'owner':'TEST','delivery_mode':'live_feed'}
 monkeypatch.setattr('habnews.config.sources',lambda:[src])
 db.conn.execute("INSERT INTO habnews_source(id,health) VALUES('0','blocked')")
 svc=ApprovalService(db,Approval(db,123,123),None,123)
 text=svc.command({'chat':{'id':123,'type':'private'},'from':{'id':123},'text':'/haber_kaynaklar'})
 assert 'kaynak erişimi engelli' in text and '90 saniyede bir' in text
