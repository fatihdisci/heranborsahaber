import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import twitter from 'twitter-text';
import {report} from '../src/kap/reports';
import {normalize,type Disclosure,type Indices} from '../src/kap/parser';
import {postText} from '../src/editorial';
import {draftCards} from '../src/card-pages';
import {OutputCapacityError,capacityMessage} from '../src/output-capacity';
import {localDatabase} from '../src/local-adapters';
import {queueManual} from '../src/manual';
import {runManual} from '../scripts/manual_reader';
import type {Env} from '../src/types';
const fixture=JSON.parse(await readFile('test/fixtures/circuit-report-2026-10-23.json','utf8')) as {at:number;indices:Indices;disclosures:Disclosure[];provenance:{kind:string}};
const records=fixture.disclosures.map(disclosure=>({disclosure}));
test('read-only reconstructed real-day cache has 475 distinct circuit notices and 400 tickers, not all 730 disclosures',()=>{
 assert.equal(fixture.provenance.kind,'reconstructed_public_kap_cache');assert.equal(records.length,730);
 const matching=records.filter(r=>normalize(r.disclosure.title+' '+r.disclosure.summary).includes('DEVRE KESICI'));
 assert.equal(matching.length,475);assert.equal(new Set(matching.map(r=>r.disclosure.id)).size,475);
 for(const {disclosure:d} of matching){assert.equal(d.title,'Pay Bazında Devre Kesici Bildirimi');assert.equal(d.disclosureClass,'DUY');assert.equal(d.disclosureType,'DUY');assert.equal(d.subjectCodes.length,1);assert.equal(d.url,'https://www.kap.org.tr/tr/Bildirim/'+d.id);assert.equal(new Date(Date.parse(d.publishedAt)+10800000).toISOString().slice(0,10),'2026-10-23');assert(Date.parse(d.publishedAt)<=fixture.at);}
 const out=report('circuit',records,fixture.indices,fixture.at,'');assert.equal(out.draft.card_data!.report!.events!.length,475);assert.equal(out.draft.card_data!.report!.rows.length,400);assert.equal(out.draft.card_data!.report!.rows.reduce((n,r)=>n+Number(r.value.split(' ')[0]),0),475);
 const tweet=twitter.parseTweet(postText(out.draft));assert.equal(tweet.weightedLength,161);assert(tweet.valid);assert.equal(out.draft.output_preferences,undefined);
 assert.throws(()=>draftCards(out.draft),(e:unknown)=>{assert(e instanceof OutputCapacityError);assert.deepEqual(e.diagnostic,{version:1,kind:'visual',fields:[{name:'report.rows',rows:400,per_card:15}],required_cards:27,max_cards:4});return true;});
 const withNoise=report('circuit',[...records,...matching.slice(0,10),{disclosure:{...matching[0].disclosure,id:9999991,publishedAt:'2026-10-22T20:59:59Z'}},{disclosure:{...matching[0].disclosure,id:9999992,publishedAt:'2026-10-23T20:09:00Z'}}],fixture.indices,fixture.at,'');assert.deepEqual(withNoise.draft.card_data,out.draft.card_data);
});
test('real-day manual command records the exact visual reason, does not render partial media or create delivery jobs, and only edits one acknowledgement',async()=>{
 const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8'));let renders=0,writes=0;const calls:{method:string;text:string}[]=[];
 const env={DB,MODE:'telegram_review',TELEGRAM_USER_ID:'7',TELEGRAM_CHAT_ID:'42',TELEGRAM_BOT_TOKEN:'123:fixture',TELEGRAM_VERIFIED_BOT_ID:'123',KAP_REPORT:async(kind:any,at:number,prefs:any)=>{assert.equal(kind,'circuit');assert.equal(at,fixture.at);assert.equal(prefs,undefined);return report(kind,records,fixture.indices,at,'',prefs);},RENDER_REPORT:async()=>{renders++;return new Uint8Array([1]);},MEDIA:{put:async()=>{writes++;}}} as unknown as Env;
 const old=globalThis.fetch;globalThis.fetch=async(url,init)=>{assert(String(url).startsWith('https://api.telegram.org/'));const method=String(url).split('/').at(-1)!;assert(['sendMessage','editMessageText'].includes(method));calls.push({method,text:(init!.body as URLSearchParams).get('text')!});return Response.json({ok:true,result:{message_id:99}});};
 try{
  await queueManual(env,1,{message_id:8,from:{id:7},chat:{id:42,type:'private'},date:fixture.at/1000,text:'/devrekesici'});await runManual(env);
  const failed=await DB.prepare('SELECT state,error,job_id,attempts FROM manual_requests').first<any>();assert.deepEqual({...failed},{state:'needs_review',error:'multi_card_capacity_exceeded',job_id:null,attempts:1});
  const stored=JSON.parse((await DB.prepare("SELECT value FROM system_state WHERE key='manual_capacity:1'").first<any>()).value);assert.equal(stored.events,475);assert.equal(stored.tickers,400);assert.equal(stored.required_cards,27);assert.equal(stored.tweet_length,161);assert.equal(stored.preference,'default_summary');assert.equal(stored.kind,'visual');
  await runManual(env);await runManual(env);assert.deepEqual(calls.map(c=>c.method),['sendMessage','editMessageText']);const text=calls[1].text;for(const pattern of [/475 bildirim/,/400 farklı hisse/,/60 hisse/,/27 kart/,/161\/280/,/tweet sınırı sorun değil/,/Hiçbir satır çıkarılmadı/])assert.match(text,pattern);
  assert.equal(renders,0);assert.equal(writes,0);for(const table of ['drafts','model_jobs','x_posts','telegram_effects'])assert.equal((await DB.prepare('SELECT COUNT(*) n FROM '+table).first<any>()).n,0);
 }finally{globalThis.fetch=old;}
});
test('explicit all-ticker tweet failure preserves the preference and reports a text limit independently of visual limits',()=>{
 assert.throws(()=>report('circuit',records,fixture.indices,fixture.at,'',{list:'all'}),(e:unknown)=>{assert(e instanceof OutputCapacityError);assert.equal(e.message,'tweet_capacity_exceeded');assert.equal(e.diagnostic.kind,'tweet');assert.equal(e.diagnostic.preference,'all');assert(e.diagnostic.tweet_length!>280);const text=capacityMessage(e.message,e.diagnostic)!;assert.match(text,/tüm-hisseler tercihin korunuyor/);assert.match(text,/görsel üretimi başlamadı/);assert.doesNotMatch(text,/dört okunaklı görsele veya/);return true;});
 assert.match(capacityMessage('multi_card_capacity_exceeded')!,/görsel kapasitesi/);assert.match(capacityMessage('report_cell_capacity_exceeded')!,/hücre/);assert.match(capacityMessage('kap_report_caption_limit')!,/Telegram açıklama/);assert.equal(capacityMessage('unrelated_error'),undefined);
});
