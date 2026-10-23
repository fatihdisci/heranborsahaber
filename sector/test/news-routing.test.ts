import {reviewFixture} from './news-readiness-fixture';
import {beforeEach,afterEach,mock as fixedClock} from 'node:test';
beforeEach(()=>fixedClock.timers.enable({apis:['Date'],now:Date.parse('2026-10-23T09:30:00Z')}));
afterEach(()=>fixedClock.timers.reset());
import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
import {evaluateNews,DEFAULT_NEWS_PREFERENCES,recordNewsCandidate,searchNewsArchive} from '../src/news-routing';import {localDatabase} from '../src/local-adapters';import type {Source,Env} from '../src/types';
import {scheduledSelection} from '../src/newsroom';
const now=Date.parse('2026-10-23T09:30:00Z'),source={id:'test',family:'publisher',official:false} as Source,p={...DEFAULT_NEWS_PREFERENCES,entities:[{name:'Örnek Holding',code:'TEST',verified:true}]};
const item=(title:string,summary='Somut açıklamanın ayrıntıları ve kaynaktaki yeni karar hakkında ek bilgi.')=>({title,summary,url:'https://example.com/'+encodeURIComponent(title),published_at:new Date(now-60000).toISOString()});
test('rules distinguish decisions, expectations, allegations, denials and material macro without a company',()=>{
 assert.equal(evaluateNews(item('TCMB politika faizi kararını açıkladı'),source,p,now).route,'instant');
 assert.equal(evaluateNews(item('TCMB politika faizi beklentisi açıklandı'),source,p,now).route,'digest');
 assert.equal(evaluateNews(item('Örnek Holding sözleşme imzaladı'),source,p,now).route,'instant');
 assert.equal(evaluateNews(item('Örnek Holding üretim durdu iddiası'),source,p,now).route,'digest');
 assert.equal(evaluateNews(item('Örnek Holding üretimin durdurulduğu iddiasını yalanladı'),source,p,now).route,'instant');
 for(const title of ['Kriz rekor faiz','Üretim durdu','Apple yeni telefon lansmanı','Faiz hakkında yorum'])assert.notEqual(evaluateNews(item(title),source,p,now).route,'instant');
 assert.equal(evaluateNews(item('Yapay zeka etkinlik tanıtımı başladı'),source,p,now).route,'archive');
 assert.equal(evaluateNews({...item('TCMB politika faizi kararını açıkladı'),published_at:null},source,p,now).route,'digest');
});
test('periods, changed amounts and decision state remain distinct; name resemblance creates no ticker',()=>{
 const a=evaluateNews(item('Örnek Holding 2026/9 bilanço açıkladı'),source,p,now),b=evaluateNews(item('Örnek Holding 2026/6 bilanço açıkladı'),source,p,now);assert.notEqual(a.identity,b.identity);
 assert.deepEqual(evaluateNews(item('Örnek Yatırım tanıtım yaptı'),source,p,now).confidence.codes,[]);
 assert.notEqual(evaluateNews(item('Örnek Holding 10 milyon TL sözleşme imzaladı'),source,p,now).identity,evaluateNews(item('Örnek Holding 20 milyon TL sözleşme imzaladı'),source,p,now).identity);
});
test('shadow retains rejected legacy candidates, searchable metadata and bounded expiry without model calls',async()=>{
 const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8')),env={DB} as Env;
 const first=await recordNewsCandidate(env,item('Örnek Holding sözleşme imzaladı'),source,false,now,p);assert(first);
 const r=await DB.prepare('SELECT legacy_eligible,rule_version,expires_at,summary FROM news_candidates').first<any>();assert.equal(r.legacy_eligible,0);assert.equal(r.expires_at,now+7*86400000);
 assert.equal((await DB.prepare('SELECT COUNT(*) n FROM model_jobs').first<any>()).n,0);
});
test('scheduled digest is off by default and restart never duplicates a delivery with unknown outcome',async()=>{
 const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8')),env={DB} as Env;let calls=0;const sender=async()=>{calls++;throw Error('timeout');};await scheduledSelection(env,now,sender);assert.equal(calls,0);
 await DB.prepare('INSERT INTO system_state VALUES(?,?)').bind('news_filter_preferences',JSON.stringify({...p,mode:'active',approved_by_owner:true,digest_enabled:true,activated_at:now-60000})).run();await reviewFixture(env,{...p,digest_enabled:true});await scheduledSelection(env,now,sender);await scheduledSelection(env,now,sender);assert.equal(calls,1);assert.equal((await DB.prepare('SELECT state FROM news_digest_runs').first<any>()).state,'uncertain');
});
test('cross-source copies group conservatively; a new amount, period or event stage remains visible',async()=>{
 const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8')),env={DB} as Env;
 const a=await recordNewsCandidate(env,item('Örnek Holding ihale kazandı'),source,true,now,p);
 const b=await recordNewsCandidate(env,{...item('Örnek Holding ihale kazandı'),url:'https://second.example/same'}, {...source,id:'second'},true,now,p);assert.equal(a.group,b.group);
 const c=await recordNewsCandidate(env,{...item('Örnek Holding sözleşme imzaladı'),url:'https://third.example/new'}, {...source,id:'third'},true,now,p);assert.notEqual(a.group,c.group);
 const row=await DB.prepare('SELECT suggestions FROM news_candidates WHERE id=?').bind(c.id).first<any>();assert(JSON.parse(row.suggestions).includes(a.id));
 const d=await recordNewsCandidate(env,{...item('Örnek Holding 2026/6 finansal tablo açıkladı'),url:'https://fourth.example/new'}, {...source,id:'fourth'},false,now,p);assert.notEqual(c.group,d.group);
});
test('digest catches a short restart delay, requires separate owner approval and retries only explicit rejection',async()=>{
 const {TelegramError}=await import('../src/telegram'),DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8')),env={DB} as Env;let calls=0;
 await DB.prepare('INSERT INTO system_state VALUES(?,?)').bind('news_filter_preferences',JSON.stringify({...p,mode:'active',digest_enabled:true,activated_at:now-60000})).run();await scheduledSelection(env,now,async()=>{calls++;});assert.equal(calls,0);
 await DB.prepare('UPDATE system_state SET value=?').bind(JSON.stringify({...p,mode:'active',approved_by_owner:true,digest_enabled:true,activated_at:now-60000})).run();
 await reviewFixture(env,{...p,digest_enabled:true});
 const sender=async()=>{calls++;if(calls===1)throw new TelegramError(429,1,'retryable');};await scheduledSelection(env,now+60000,sender);assert.equal(calls,1);await scheduledSelection(env,now+62000,sender);assert.equal(calls,2);await scheduledSelection(env,now+63000,sender);assert.equal(calls,2);
});
test('same URL changes retain a new stable version rather than overwriting the old event',async()=>{
 const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8')),env={DB} as Env,first=item('Örnek Holding 10 milyon TL sözleşme imzaladı');
 const a=await recordNewsCandidate(env,first,source,true,now,p),second={...first,title:'Örnek Holding 20 milyon TL sözleşme imzaladı'};
 const b=await recordNewsCandidate(env,second,source,true,now+1,p),c=await recordNewsCandidate(env,second,source,true,now+2,p);assert.notEqual(a.id,b.id);assert.equal(b.id,c.id);assert.notEqual(a.group,b.group);assert.equal((await DB.prepare('SELECT COUNT(*) n FROM news_candidates').first<any>()).n,2);
});
test('forwarded source text cannot invoke editor commands or permanently label candidates',async()=>{
 const {newsroomMessage}=await import('../src/newsroom');assert.equal(await newsroomMessage({} as Env,{text:'/haberfiltre',forward_origin:{type:'hidden_user'}}),false);
});
test('promotion context cannot silently archive a concrete important decision',()=>{
 assert.equal(evaluateNews(item('TCMB konferans: politika faizi kararını açıkladı'),source,p,now).route,'instant');
 assert.equal(evaluateNews(item('TCMB webinar ve konferans duyurusu'),source,p,now).route,'archive');
});
test('identical same-publisher copies also group, while an amount change stays separate',async()=>{
 const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8')),env={DB} as Env,a=item('Örnek Holding 10 milyon TL sözleşme imzaladı');
 const first=await recordNewsCandidate(env,a,source,true,now,p),copy=await recordNewsCandidate(env,{...a,url:a.url+'-copy'},source,true,now+1,p);assert.equal(first.group,copy.group);assert(copy.decision.reasons.includes('same_event_copy'));
 const changed=await recordNewsCandidate(env,{...a,url:a.url+'-changed',title:'Örnek Holding 20 milyon TL sözleşme imzaladı'},source,true,now+2,p);assert.notEqual(first.group,changed.group);
});
