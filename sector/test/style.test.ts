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
