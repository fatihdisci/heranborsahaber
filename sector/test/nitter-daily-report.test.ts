import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
import {localDatabase} from '../src/local-adapters';import type {Env} from '../src/types';
import {buildAccountReport,istanbulDate,parseAccountRss,type AccountSnapshot} from '../src/nitter-account';
import {dailyReportDue,dailyReportKey,dailyAccountKey,observeAccountPosts,sendDailyAccountReport} from '../src/nitter-daily-report';
import {TelegramError} from '../src/telegram';

const iso=(mins:number)=>new Date(Date.now()+mins*60_000).toUTCString();
function rss(rows:{id:string;at:string;title?:string}[],account='endeks_haber'){
 return `<rss><channel><title>ENDEKS HABER / @${account}</title>${rows.map(r=>`<item><title>${r.title??'Gönderi'}</title><link>https://nitter.meowing.monster/${account}/status/${r.id}</link><pubDate>${r.at}</pubDate><description><![CDATA[<p>tweet</p>]]></description></item>`).join('')}</channel></rss>`;
}
async function envSetup(){const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8'));return {DB} as Env;}

test('Nitter account RSS validates identity and tweet URLs, rejecting challenges and unsafe XML',()=>{
 const xml=rss([{id:'123',at:iso(-20)}]);const p=parseAccountRss(xml)[0];assert.equal(p.id,'123');assert.equal(p.url,'https://x.com/endeks_haber/status/123');assert.equal(p.retweet,false);
 assert.throws(()=>parseAccountRss(rss([{id:'123',at:iso(-20)}],'someone_else')),/account_mismatch/);
 assert.throws(()=>parseAccountRss('<!DOCTYPE rss><rss/>'),/unsafe/);assert.throws(()=>parseAccountRss('<html>challenge</html>'),/account_mismatch/);
 assert.equal(parseAccountRss(rss([{id:'124',at:iso(-10),title:'RT by @other'}]))[0].retweet,true);
});

test('Istanbul calendar boundary and 23:00 report trigger are explicit',()=>{
 assert.equal(istanbulDate(Date.parse('2026-10-22T20:59:59Z')),'2026-10-22');
 assert.equal(istanbulDate(Date.parse('2026-10-22T21:00:00Z')),'2026-10-23');
 assert.equal(dailyReportDue(Date.parse('2026-10-23T19:59:59Z')),false);
 assert.equal(dailyReportDue(Date.parse('2026-10-23T20:00:00Z')),true);
});

test('daily Nitter observations merge tweet IDs across the RSS latest-20 window and preserve data on outage',async()=>{
 const env=await envSetup(),now=Date.now(),day=istanbulDate(now);const posts=(ids:string[]):AccountSnapshot=>({posts:ids.map((id,i)=>({id,at:new Date(now-(ids.length-i)*60_000).toISOString(),url:`https://x.com/endeks_haber/status/${id}`,retweet:false})),hosts:['nitter.meowing.monster'],truncated:false});
 await observeAccountPosts(env,now,async()=>posts(['1','2']));await observeAccountPosts(env,now+1,async()=>posts(['2','3']));
 const stored=JSON.parse((await env.DB.prepare('SELECT value FROM system_state WHERE key=?').bind(dailyAccountKey(day)).first<{value:string}>())!.value);assert.deepEqual(stored.posts.map((p:any)=>p.id),['1','2','3']);
 const failed=await observeAccountPosts(env,now+2,async()=>{throw Error('offline');});assert.equal(failed.ok,false);assert.equal(failed.value?.posts.length,3);
 const health=JSON.parse((await env.DB.prepare("SELECT value FROM system_state WHERE key='nitter_account_health'").first<{value:string}>())!.value);assert.equal(health.ok,false);assert.equal(health.failures,1);
});

test('daily report analyzes actual tweet intervals and sends only once, without trusting manual marks',async()=>{
 const env=await envSetup(),now=Date.now(),day=istanbulDate(now),base=Date.parse(`${day}T23:00:00+03:00`),calls:{send:number;load:number}={send:0,load:0};
 const snapshot:AccountSnapshot={posts:[0,25,90].map((m,i)=>({id:String(i+1),at:new Date(base-180*60_000+m*60_000).toISOString(),url:`https://x.com/endeks_haber/status/${i+1}`,retweet:false})),hosts:['nitter.meowing.monster'],truncated:false};
 const load=async()=>{calls.load++;return snapshot;};await observeAccountPosts(env,base-60_000,load);
 const result=await sendDailyAccountReport(env,base,load,async text=>{calls.send++;assert.match(text,/Görülen özgün gönderi: 3/);assert.match(text,/Aralıklar: 25 dk · 1 sa 5 dk/);assert.match(text,/ortalama 45 dk/);return {message_id:99};});
 assert.equal(result.state,'sent');assert.equal(calls.send,1);assert.equal(calls.load,2);
 const again=await sendDailyAccountReport(env,base+30_000,load,async()=>{calls.send++;});assert.equal(again.state,'sent');assert.equal(calls.send,1);
 const saved=JSON.parse((await env.DB.prepare('SELECT value FROM system_state WHERE key=?').bind(dailyReportKey(day)).first<{value:string}>())!.value);assert.equal(saved.message_id,99);assert.equal(saved.state,'sent');
});

test('a failed final Nitter fetch never reports a confident zero; an unknown Telegram delivery is not resent',async()=>{
 const env=await envSetup(),now=Date.now(),day=istanbulDate(now),at=Date.parse(`${day}T23:00:00+03:00`);let sends=0;
 const result=await sendDailyAccountReport(env,at,async()=>{throw Error('all mirrors down');},async text=>{sends++;assert.match(text,/erişilemedi/);assert.match(text,/eksik olabilir/);throw new TelegramError(0,60,'uncertain');});
 assert.equal(result.state,'uncertain');assert.equal(sends,1);
 const again=await sendDailyAccountReport(env,at+3*60_000,async()=>({posts:[],hosts:[],truncated:false}),async()=>{sends++;});assert.equal(again.state,'uncertain');assert.equal(sends,1);
});

test('report preserves retweet context and flags a capped feed',()=>{
 const day=istanbulDate(Date.now()),report=buildAccountReport(day,[{id:'1',at:new Date().toISOString(),url:'https://x.com/endeks_haber/status/1',retweet:false},{id:'2',at:new Date().toISOString(),url:'https://x.com/endeks_haber/status/2',retweet:true}],{ok:true,hosts:['nitter.meowing.monster'],truncated:true});
 assert.match(report,/özgün gönderi: 1 · retweet: 1/);assert.match(report,/20 kayıt sınırına ulaştı/);
});
