import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {marketPeriod,withMarketTiming} from '../src/market-timing';
import {repairDraftStyle} from '../src/style';
import {queueManual} from '../src/manual';
import {manualDocuments} from '../scripts/manual_reader';
import {localDatabase} from '../src/local-adapters';
import type {Document,Draft,Env} from '../src/types';
const stamp=(t:string)=>Date.parse('2026-10-22T'+t+':00+03:00')/1000;
const source:Document={source_id:'manual-input',source_name:'Belge',family:'owner-submitted',official:false,url:'https://example.test/input',title:'KTLEV AKD',body:'KTLEV aracı kurum dağılımı',published_at:null,language:'tr',passages:[{id:'p1',text:'KTLEV aracı kurum dağılımı'}],market_data:{kind:'akd',ticker:'KTLEV'}};
test('Istanbul submission windows have exact boundaries and no overnight default',()=>{
 for(const [t,label] of [['09:59',undefined],['10:00','Açılışın ilk dakikaları'],['10:59','Açılışın ilk dakikaları'],['11:00','Gün ortası'],['13:59','Gün ortası'],['14:00','Kapanışa doğru'],['17:59','Kapanışa doğru'],['18:00','Gün sonu'],['21:59','Gün sonu'],['22:00',undefined]] as const)assert.equal(marketPeriod(stamp(t)),label);
 assert.equal(marketPeriod(NaN),undefined);assert.equal(marketPeriod(-1),undefined);
});
test('submission period survives retries and edits; historical source dates take precedence',()=>{
 const d=withMarketTiming(source,stamp('12:15'));assert.equal(d.market_data?.editorial_period,'Gün ortası');assert.deepEqual(withMarketTiming(d,stamp('19:00')),d);
 assert.equal(withMarketTiming(source).market_data?.editorial_period,undefined);
 for(const date of ['2026-10-21','21.10.2026','21-10-2026','21 Ekim 2026'])assert.equal(withMarketTiming({...source,body:date},stamp('12:15')).market_data?.editorial_period,undefined);
 assert.equal(withMarketTiming({...source,body:'22 Ekim 2026'},stamp('12:15')).market_data?.editorial_period,'Gün ortası');
 const value={headline:'📊 KTLEV aracı kurum dağılımı',body:'Kurum dağılımı açıklandı.',card_headline:'KTLEV aracı kurum dağılımı',card_body:'Kurum dağılımı.',hashtags:['#Borsa','#BIST','#KTLEV']} as Draft;
 const fixed=repairDraftStyle(value,[d]);assert(fixed.headline.startsWith('📊 Gün ortası —'));assert(fixed.card_headline.startsWith('Gün ortası —'));assert.deepEqual(repairDraftStyle(fixed,[d]),fixed);
});
test('Telegram original message timestamp, not processing or selection time, reaches market documents',async()=>{
 const env={DB:await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8')),MODE:'dry_run',TELEGRAM_USER_ID:'7',TELEGRAM_CHAT_ID:'42'} as Env;
 const text=await readFile('test/fixtures/bopt.txt','utf8');
 await queueManual(env,900,{message_id:901,date:stamp('19:00'),text:'Sadece alınanlar',from:{id:7},chat:{id:42,type:'private'},reply_to_message:{message_id:800,date:stamp('10:30'),text}});
 const row=await env.DB.prepare('SELECT kind,input FROM manual_requests WHERE update_id=900').first<{kind:string;input:string}>();const docs=await manualDocuments(env,row!.kind,row!.input,901);
 assert.equal(docs[0].market_data?.editorial_period,'Açılışın ilk dakikaları');assert.equal(docs[0].market_data?.submitted_at,stamp('10:30'));assert.equal(docs[0].published_at,null);
});
