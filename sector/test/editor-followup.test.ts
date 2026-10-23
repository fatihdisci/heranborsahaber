import test,{beforeEach,afterEach,mock} from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {outputPreferences,outputView,tweetListLimit} from '../src/output-preferences';
import {draftCard} from '../src/card';import {png} from '../scripts/render_local';
import {generalBuyback} from '../src/general-buyback';import {evidenceView} from '../src/editor-tools';
import {enqueueEdit} from '../src/bridge';import {localDatabase} from '../src/local-adapters';
import {DEFAULT_NEWS_PREFERENCES,NEWS_RULE_VERSION,newsPreferences} from '../src/news-routing';
import {newsReadiness,digestDeliveryStatus} from '../src/news-readiness';
import {newsroomMessage,scheduledSelection} from '../src/newsroom';
import {announceNews} from '../src/news-inbox';import {reviewFixture} from './news-readiness-fixture';
import type {Draft,Env,Source} from '../src/types';
const at=Date.parse('2026-10-23T09:30:00Z');
beforeEach(()=>mock.timers.enable({apis:['Date'],now:at}));afterEach(()=>mock.timers.reset());
const pref={list:'first' as const,count:3,side:'sell' as const,show_time:true,show_footer:true,presentation:'frame'};
const d={headline:'📢 Kurum işlemleri',body:'Doğrulanmış işlemler.',hashtags:[],card_headline:'İşlemler',card_body:'Kaynak verileri.',category:'bist',importance:80,template:'institutional',claims:[],entities:[],event_key:'fixture',uncertainties:[],card_data:{broker:'BofA',buy:[{label:'ABCD',value:'10 TL'}],sell:[{label:'SELL',value:'20 TL'}]}} as Draft;
async function setup(){return {DB:await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8')),TELEGRAM_USER_ID:'7',TELEGRAM_CHAT_ID:'7',TELEGRAM_BOT_TOKEN:'123:fixture',TELEGRAM_VERIFIED_BOT_ID:'123',MODE:'telegram_review'} as Env;}
const prefs={...DEFAULT_NEWS_PREFERENCES,mode:'active' as const,approved_by_owner:true,digest_enabled:true,activated_at:at-60000,entities:[{name:'Örnek Holding',code:'TEST',verified:true}]};
const savePrefs=(e:Env,p:unknown)=>e.DB.prepare('INSERT INTO system_state VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value').bind('news_filter_preferences',JSON.stringify(p)).run();
function transport(){const original=globalThis.fetch,texts:string[]=[];globalThis.fetch=async(_u,init)=>{const body=init?.body as URLSearchParams;texts.push(body instanceof FormData?'document':String(body.get('text')));return Response.json({ok:true,result:{message_id:texts.length+100}});};return {texts,restore:()=>globalThis.fetch=original};}
test('first-N consumes every digit and rejects unsupported, fractional, zero and negative limits',()=>{
 assert.equal(outputPreferences('ilk 100 hisse')!.count,100);assert.equal(outputPreferences('ilk 999 hisse')!.count,999);
 for(const text of ['ilk 1000','ilk 10000','ilk 999999999999999999999999','ilk 0','ilk -2','ilk 3,5','ilk 1.5','ilk 1.000','ilk 1e3'])assert.throws(()=>outputPreferences(text),/unsupported_output_limit/,text);
 assert.throws(()=>outputView({...d,output_preferences:{list:'first',count:1000}}),/invalid_output_limit/);assert.throws(()=>outputView({...d,card_data:undefined,output_preferences:{list:'first',count:1000}}),/invalid_output_limit/);
});
test('time-only updates preserve list, side, footer and presentation; absent scope keeps product defaults',()=>{
 assert.deepEqual(outputPreferences('saat yazma',pref),{...pref,show_time:false});assert.deepEqual(outputPreferences('saat göster'),{show_time:true});assert.deepEqual(outputPreferences('saat göster alt not olmasın',pref),{...pref,show_footer:false});
 const view=outputView({...d,output_preferences:outputPreferences('saat yazma')});assert.equal(view.card_data!.buy!.length,1);assert.equal(view.card_data!.sell!.length,1);assert.equal(tweetListLimit(view,5),5);
});
test('footer-only updates preserve list and other unspecified fields, including time',()=>{
 assert.deepEqual(outputPreferences('alt not olmasın',pref),{...pref,show_footer:false});assert.deepEqual(outputPreferences('saat yazma, alt not göster',pref),{...pref,show_time:false});
 assert.equal(outputPreferences('başlığı düzelt',pref),undefined);
});
test('side-only updates preserve first-N and footer/time; explicit all clears only the obsolete count',()=>{
 assert.deepEqual(outputPreferences('sadece alınanlar',pref),{...pref,side:'buy'});assert.deepEqual(outputPreferences('her iki taraf',pref),{...pref,side:'both'});
 assert.deepEqual(outputPreferences('tümünü yaz',pref),{list:'all',side:'sell',show_time:true,show_footer:true,presentation:'frame'});
});
test('queued edit merges stored preferences instead of resetting scope for a decorative change',async()=>{
 const env=await setup();await env.DB.prepare("INSERT INTO sources(id,config) VALUES('manual-input','{}')").run();await env.DB.prepare("INSERT INTO articles(id,source_id,url,title,summary,published_at,first_seen,draft_id) VALUES('a','manual-input','https://example.org/source','Kaynak','','2026-10-23',1,'d')").run();
 const doc={source_id:'manual-input',source_name:'Kaynak',family:'manual',official:false,url:'https://example.org/source',title:'Kaynak',body:'Doğrulanmış kaynak verileri.',passages:[{id:'p1',text:'Doğrulanmış kaynak verileri.'}],published_at:null};
 await env.DB.prepare("INSERT INTO drafts(id,event_key,fingerprint,content,documents,verification,created_at,expires_at) VALUES('d','e','f',?,?,'verified',1,9999999999)").bind(JSON.stringify({...d,output_preferences:pref}),JSON.stringify([doc])).run();
 await enqueueEdit(env,'d',1,'alt not olmasın');const job=await env.DB.prepare('SELECT documents FROM model_jobs').first<any>();assert.deepEqual(JSON.parse(job.documents)[0].output_preferences,{...pref,show_footer:false});
});
test('unsupported first-N command returns an explicit owner error without queuing truncated work',async()=>{
 const {queueManual}=await import('../src/manual'),env=await setup(),t=transport();try{assert(await queueManual(env,123,{message_id:88,text:'/gerialım ilk 1000',from:{id:7},chat:{id:7,type:'private'}}));assert(t.texts[0].includes('1–999'));assert.equal((await env.DB.prepare('SELECT COUNT(*) n FROM manual_requests').first<any>()).n,0);}finally{t.restore();}
});
test('general buyback actual SVG/PNG hides optional footer while partial totals and editor evidence survive',async()=>{
 const result=generalBuyback('general_buyback',[],null,at,'Kısmi tarama kapsamı; eksik kayıt olabilir.');
 const g={partial:true,day:'2026-10-23',time:'12:30',companies:1,lots:'123',amount:'0,00',missing:1,rows:[{ticker:'ABCD',lots:'123',price:'—',amount:'—',urls:'https://www.kap.org.tr/tr/Bildirim/fixture'}]};
 const draft={...result.draft,card_data:{report:{...result.draft.card_data!.report!,general:g}},source_notes:[...result.draft.source_notes!,'Eksik fiyat; toplam tutar kısmi.']};
 const shown=draftCard({...draft,output_preferences:{show_footer:true}}),hidden=draftCard({...draft,output_preferences:{show_footer:false}});
 assert(shown.includes('Yalnız KAP'));assert(shown.includes('Toplayıcı kapsamı kısmi'));assert(!hidden.includes('Yalnız KAP'));assert(!hidden.includes('Eksik fiyatlar'));
 assert(hidden.includes('TOPLAM TUTAR (KISMİ)'));assert(hidden.includes('—'));assert(!hidden.includes('12:30'));
 const view=outputView({...draft,output_preferences:{show_footer:false}});assert(evidenceView(view,result.documents,'verified').source_notes.some(n=>n.includes('Kısmi tarama')));
 const [a,b]=await Promise.all([png(shown),png(hidden)]);for(const bytes of [a,b])assert.equal(Buffer.from(bytes).toString('hex',0,8),'89504e470d0a1a0a');assert.notEqual(createHash('sha256').update(a).digest('hex'),createHash('sha256').update(b).digest('hex'));
 // Saved outside the repo solely for visual inspection of the real render.
 await mkdir('/tmp/endeks-editor-followup',{recursive:true});await writeFile('/tmp/endeks-editor-followup/general-footer-hidden.svg',hidden);await writeFile('/tmp/endeks-editor-followup/general-footer-hidden.png',b);await writeFile('/tmp/endeks-editor-followup/general-footer-shown.png',a);
});
test('configured digest clearly reports delivery disabled in shadow mode; no readiness is fabricated',async()=>{
 const env=await setup(),t=transport();try{await savePrefs(env,prefs);await newsroomMessage(env,{text:'/haberfiltre'});assert(t.texts[0].includes('Seçki yapılandırması: açık'));assert(t.texts[0].includes('gölge modda gönderim kapalı'));assert(t.texts[0].includes('hazırlık kontrolünde durduruldu'));const p=await newsPreferences(env);assert.equal(p.mode,'shadow');assert.equal(digestDeliveryStatus(p),false);assert.equal(await env.DB.prepare("SELECT value FROM system_state WHERE key='news_filter_readiness'").first(),null);
 let sends=0;await scheduledSelection(env,at,async()=>{sends++;});assert.equal(sends,0);
 }finally{t.restore();}
});
test('active mode requires versioned mapping, scope and actual human-labelled shadow evaluation',async()=>{
 const env=await setup();await savePrefs(env,prefs);assert.equal((await newsPreferences(env)).mode,'shadow');
 const record=await reviewFixture(env,prefs);const ready=await newsReadiness(env,prefs,NEWS_RULE_VERSION);assert.equal(ready.metrics.reviewed,12);assert.equal(ready.ready,true);assert.equal((await newsPreferences(env)).mode,'active');
 for(const field of ['entity_review','scope_review','evaluation_review','version','rule_version']){const copy={...record};delete (copy as any)[field];await env.DB.prepare("UPDATE system_state SET value=? WHERE key='news_filter_readiness'").bind(JSON.stringify(copy)).run();assert.equal((await newsPreferences(env)).mode,'shadow',field);}
 await env.DB.prepare("UPDATE system_state SET value=? WHERE key='news_filter_readiness'").bind(JSON.stringify({...record,evaluation_review:{...record.evaluation_review,hash:'invented'}})).run();assert.equal((await newsPreferences(env)).mode,'shadow');
 await env.DB.prepare("UPDATE system_state SET value=? WHERE key='news_filter_readiness'").bind(JSON.stringify(record)).run();
 await savePrefs(env,{...prefs,watchlist:['TEST']});assert.equal((await newsPreferences(env)).mode,'shadow');await savePrefs(env,prefs);
 for(const activated_at of [0,at+60000]){await savePrefs(env,{...prefs,activated_at});assert.equal((await newsPreferences(env)).mode,'shadow');}await savePrefs(env,prefs);
 await env.DB.prepare("DELETE FROM news_feedback").run();const absent=await newsReadiness(env,prefs,NEWS_RULE_VERSION);assert.equal(absent.metrics.reviewed,0);assert.equal(absent.ready,false);
});
test('digest disabled keeps active request in shadow with the important-company invisibility risk explicit',async()=>{
 const env=await setup(),p={...prefs,digest_enabled:false};await savePrefs(env,p);await reviewFixture(env,p);const effective=await newsPreferences(env);assert.equal(effective.mode,'shadow');assert(effective.readiness_reasons!.some(r=>r.includes('görünmez')));
});
test('changed labels, rule version, unverified evidence and measurable routing errors invalidate readiness',async()=>{
 const env=await setup();await savePrefs(env,prefs);const record=await reviewFixture(env,prefs);
 for(const change of [{...record,rule_version:'obsolete'}, {...record,entity_review:{...record.entity_review,sources:record.entity_review.sources.map(s=>({...s,url:'https://unverified.example/TEST'}))}}]){await env.DB.prepare("UPDATE system_state SET value=? WHERE key='news_filter_readiness'").bind(JSON.stringify(change)).run();assert.equal((await newsPreferences(env)).mode,'shadow');}
 await env.DB.prepare("UPDATE system_state SET value=? WHERE key='news_filter_readiness'").bind(JSON.stringify(record)).run();await env.DB.prepare("UPDATE news_feedback SET kind='review:instant' WHERE candidate_id=(SELECT id FROM news_candidates WHERE route='archive' LIMIT 1)").run();const report=await newsReadiness(env,prefs,NEWS_RULE_VERSION);assert(report.metrics.critical_misses>0);assert.equal(report.ready,false);assert.equal((await newsPreferences(env)).mode,'shadow');
});
for(const mode of ['shadow','active'] as const)test(mode+': sustained arrivals do not starve old eligible news or replay uncertain sends; active critical priority survives',async()=>{
 const env=await setup(),t=transport();try{
 await savePrefs(env,{...prefs,mode});if(mode==='active')await reviewFixture(env,prefs);await env.DB.prepare('INSERT INTO system_state VALUES(?,?)').bind('news_preview_since',new Date(at-86400000).toISOString()).run();
 const source={id:'load',name:'Offline load fixture',family:'fixture',minimum_score:0,editorial_priority:50,official:false} as Source;await env.DB.prepare('INSERT INTO sources(id,config,enabled) VALUES(?,?,1)').bind(source.id,JSON.stringify(source)).run();
 let seq=0;const add=async(title:string,seen:number,critical=false)=>{const id=(++seq).toString(16).padStart(32,'0'),date=new Date(seen).toISOString();await env.DB.prepare('INSERT INTO articles(id,source_id,url,title,summary,published_at,first_seen) VALUES(?,?,?,?,?,?,?)').bind(id,source.id,'https://example.org/load/'+id,title,'Sabit kaynak metni ve doğrulanmış açıklama ayrıntıları.',date,Math.floor(seen/1000)).run();await env.DB.prepare('INSERT INTO news_candidates(id,article_id,url,source_id,title,summary,published_at,first_seen,expires_at,route,reasons,confidence,rule_version,evaluated_at,legacy_eligible,eligible,signature,event_group,suggestions,family) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)').bind(id,id,'https://example.org/load/'+id,source.id,title,'Kaynak metni',date,seen,at+86400000,'instant','[]',JSON.stringify({priority:0,event:critical?'rate':'financial'}),NEWS_RULE_VERSION,seen,1,1,id,id,'[]','fixture').run();return id;};
 const old:string[]=[];for(let i=0;i<20;i++)old.push(await add('Eski uygun haber '+i,at-3600000+i));
 const uncertain=await add('Belirsiz teslimat tekrar gönderilmez',at-7200000);await env.DB.prepare("INSERT INTO news_cards(id,article_id,state,created_at) VALUES(? ,?,'uncertain',?)").bind(crypto.randomUUID(),uncertain,at/1000).run();
 for(let round=0;round<40;round++){
  mock.timers.tick(60000);for(let i=0;i<6;i++)await add(`Yeni ${round} rutin ${i}`,Date.now());for(let i=0;i<2;i++)await add(`Kritik ${round} karar ${i}`,Date.now(),true);
  const before=t.texts.length;await announceNews(env);const batch=t.texts.slice(before);assert.equal(batch.length,3);if(mode==='active'){assert(batch[0].includes('Kritik '+round));assert(batch[1].includes('Kritik '+round));}
 }
 for(const id of old)assert.equal((await env.DB.prepare('SELECT state FROM news_cards WHERE article_id=?').bind(id).first<any>())?.state,'sent',id);
 assert.equal(t.texts.length,120);assert.equal(new Set(t.texts).size,120);assert(!t.texts.some(text=>text.includes('Belirsiz teslimat')));
 assert.equal((await env.DB.prepare('SELECT COUNT(*) n FROM model_jobs').first<any>()).n,0);
 }finally{t.restore();}
});
