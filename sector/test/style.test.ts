import test from 'node:test';
import assert from 'node:assert/strict';
import {editorialPolicy,hasPublisherAttribution,styleIssues} from '../src/style';
import type {Document,Draft} from '../src/types';
const doc=(v:Partial<Document>):Document=>({source_id:'test',source_name:'CNBC-e',family:'test',official:false,url:'https://example.test',title:'Haber',body:'Haber içeriği',passages:[],published_at:null,...v});
test('verified KAP equity uses Borsa, BIST and exact main code',()=>{
 assert.deepEqual(editorialPolicy([doc({official:true,source_id:'kap',equity_codes:['THYAO'],body:'Şirket yeni sözleşmesini duyurdu.'})]).required_hashtags,['#Borsa','#BIST','#THYAO']);
 assert.deepEqual(editorialPolicy([doc({body:'BIST: TUREX pay geri alımı yaptı.'})]).required_hashtags,['#Borsa','#BIST','#TUREX']);
 assert.deepEqual(editorialPolicy([doc({equity_codes:['THYAO','TAVHL']})]).required_hashtags,['#Borsa','#BIST']);
});
test('foreign equities and acronyms do not invent BIST tickers',()=>{
 assert.deepEqual(editorialPolicy([doc({title:'Tesla ve SpaceX birleşme ihtimali',body:'NASDAQ, NASA ve CNBC gelişmeyi takip ediyor.'})]).required_hashtags,[]);
 assert.deepEqual(editorialPolicy([doc({title:'Borsa İstanbul yükseldi',body:'SPK ve TCMB açıklama yaptı.'})]).required_hashtags,['#Borsa','#BIST']);
});
test('publisher attributions are rejected while true speaker and uncertainty remain valid',()=>{
 for(const text of ['CNBC-e’nin haberine göre birleşme gündemde.','Reuters’a göre şirket plan hazırlıyor.','Kaynak: Bloomberg HT','CNBC-e aktardığına göre yeni karar açıklandı.'])assert(hasPublisherAttribution(text,['CNBC-e','Reuters','Bloomberg HT']),text);
 for(const text of ['Musk, birleşme ihtimalini gündeme getirdi.','Şirket, işlemin onaya bağlı olduğunu açıkladı.','Birleşme planlandığı iddia edildi.','CNBC yeni yayın merkezini açacağını duyurdu.'])assert(!hasPublisherAttribution(text,['CNBC']),text);
 const draft={headline:'Şirket sözleşme imzaladı',body:'Açıklama yapıldı.',card_headline:'Yeni sözleşme',card_body:'Açıklama yapıldı.',hashtags:['#Borsa','#BIST','#THYAO']} as Draft;
 assert.deepEqual(styleIssues(draft,[doc({equity_codes:['THYAO']})]),[]);
 assert(styleIssues({...draft,hashtags:['#Şirket','#Yatırım']},[doc({equity_codes:['THYAO']})]).includes('missing_market_hashtags'));
});

import {headlineWithEmoji,invalidEmojiPlacement} from '../src/style';
test('one leading emoji only; body, tags, card text and trailing or compound emoji are rejected',()=>{
 const d={headline:'📢 Şirket yeni yatırımını açıkladı',body:'İzin süreci devam ediyor.',card_headline:'Yeni yatırım planı',card_body:'İzin süreci sürüyor.',hashtags:['#Borsa','#BIST']} as Draft;
 assert.equal(headlineWithEmoji('Şirket yatırım planlıyor'),'📢 Şirket yatırım planlıyor');
 assert.equal(headlineWithEmoji(d.headline),d.headline);
 assert.equal(invalidEmojiPlacement(d),false);
 assert.equal(invalidEmojiPlacement({...d,headline:'🚨 Acil açıklama yapıldı'}),false);
 for(const change of [{headline:'📢🚨 Açıklama'},{headline:'Açıklama 📢'},{headline:'📢 Açıklama 🚨'},{body:'Açıklama 📊'},{card_body:'📈 Yatırım arttı'},{hashtags:['#Borsa','📢#BIST']},{headline:'🇹🇷 Açıklama'},{headline:'👩‍💻 Açıklama'}])assert(invalidEmojiPlacement({...d,...change}));
});
test('fund categories override equity tags and do not match unrelated word fragments',()=>{
 for(const title of ['Fon tasfiyesi açıklandı','Yatırım fonlarının getirisi','Fonların ödeme süreci','TEFAS işlemleri','PBLK açıklaması'])assert.deepEqual(editorialPolicy([doc({title,equity_codes:['TEST']})]).required_hashtags,['#Fon','#PBLK','#Tasfiye']);
 for(const title of ['Telefon satışları arttı','Şirket fonlama sağladı','Yeni fonksiyon duyuruldu'])assert.deepEqual(editorialPolicy([doc({title})]).required_hashtags,[]);
});

test('KAP empty fund fields and buyback budgets do not override company tags',()=>{
 const body='İlgili Fonlar\nRelated Funds\n[]\nGeri Alım İçin Ayrılan Fonun Toplam Tutarı (TL): 1.400.000.000';
 for(const [title,code] of [['BÜLBÜLOĞLU VİNÇ — Yeni İş İlişkisi','BVSAN'],['CVK MADEN — Payların Geri Alınmasına İlişkin Bildirim','CVKMD']]){
  assert.deepEqual(editorialPolicy([doc({source_id:'kap',official:true,title,body,equity_codes:[code]})]).required_hashtags,['#Borsa','#BIST','#'+code]);
 }
 assert.deepEqual(editorialPolicy([doc({source_id:'kap',title:'Özel Durum Açıklaması',body:'Yatırım fonlarının tasfiye sürecine ilişkin açıklama.',equity_codes:['TEST']})]).required_hashtags,['#Fon','#PBLK','#Tasfiye']);
});

import {repairDraftStyle} from '../src/style';
test('KAP company attachments do not turn financial reports into fund stories',()=>{
 const docs=[doc({source_id:'kap',official:true,title:'Finansal Rapor',equity_codes:['KLGYO']}),doc({source_id:'kap_pdf',official:true,title:'Bilanço eki',body:'Şirket fon kaynaklarını ve yatırım fonlarını muhasebe dipnotunda açıkladı.'})];
 assert.deepEqual(editorialPolicy(docs).required_hashtags,['#Borsa','#BIST','#KLGYO']);
 const original={headline:'Kiler finansal sonuçlarını açıkladı',body:'Faaliyet sonuçları duyuruldu.',hashtags:['#Fon','#PBLK','#Tasfiye']} as Draft;
 const fixed=repairDraftStyle(original,docs);
 assert.deepEqual(fixed.hashtags,['#Borsa','#BIST','#KLGYO']);assert.equal(fixed.body,original.body);
 assert.deepEqual(repairDraftStyle(fixed,docs),fixed);assert.deepEqual(original.hashtags,['#Fon','#PBLK','#Tasfiye']);
});
test('missing mandatory tags are repaired without a model call or invented ticker',()=>{
 const d={headline:'Yatırım açıklaması',hashtags:['#Yeni Yatırım','#İş-Dünyası']} as Draft;
 assert.deepEqual(repairDraftStyle(d,[doc({equity_codes:['THYAO']})]).hashtags,['#Borsa','#BIST','#THYAO']);
 assert.deepEqual(repairDraftStyle(d,[doc({title:'Fon tasfiyesi'})]).hashtags,['#Fon','#PBLK','#Tasfiye']);
 assert.deepEqual(repairDraftStyle(d,[doc({title:'Tesla yatırım planlıyor'})]).hashtags,['#YeniYatırım','#İşDünyası']);
});
