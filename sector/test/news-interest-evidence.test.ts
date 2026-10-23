import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
import {localDatabase} from '../src/local-adapters';import {interestReportData,formatInterestReport} from '../src/news-interest-report';import {newsMenuCallback} from '../src/news-menu';import {recordNewsCandidate} from '../src/news-routing';import type {Env,Source} from '../src/types';
const schema=await readFile('migrations/0001_sector.sql','utf8'),at=Date.parse('2026-10-23T12:00:00Z');
async function setup(){const DB=await localDatabase(':memory:',schema),env={DB,TELEGRAM_USER_ID:'owner',TELEGRAM_CHAT_ID:'owner',TELEGRAM_BOT_TOKEN:'123:fake',TELEGRAM_VERIFIED_BOT_ID:'123'} as Env;await DB.prepare("INSERT INTO sources(id,config) VALUES('s','{\"name\":\"Kaynak\"}')").run();return env;}
test('complete feedback ledger includes >100, removed, unmatched and expired candidates; legacy snapshot remains unknown',async()=>{
 const e=await setup();for(let i=0;i<121;i++)await e.DB.prepare('INSERT INTO news_interests VALUES(?,?,?,?,?,?,?)').bind('owner','a'+i,null,'s',i===120?null:i%2?'like':'dislike',i,at).run();await e.DB.prepare("INSERT INTO news_interests VALUES('other','private',NULL,'s','like',999,0)").run();
 const data=await interestReportData(e),text=formatInterestReport(data,at);assert.equal(data.records.length,121);assert(text.includes('a0'));assert(text.includes('a120'));assert(!text.includes('private'));assert.match(text,/YOK — geçmiş karar/);assert.match(text,/silinmiş\/eşleşmedi/);
});
test('applied click stores decision then toggle/remove; duplicate/older receipt cannot rewrite snapshots or votes',async()=>{
 const e=await setup(),source={id:'s'} as Source,item={url:'https://example.org/a',title:'Aselsan sözleşme imzaladı',summary:'Resmî açıklamaya göre sözleşme bugün imzalandı.',published_at:new Date(at).toISOString()};
 const n=await recordNewsCandidate(e,item,source,true,at);await e.DB.prepare('INSERT INTO articles(id,source_id,url,title,summary,published_at,first_seen) VALUES(?,?,?,?,?,?,?)').bind(n.article,'s',item.url,item.title,item.summary,item.published_at,at/1000).run();const id='bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb';await e.DB.prepare("INSERT INTO news_cards(id,article_id,state,message_id,created_at) VALUES(?,?,'sent',80,?)").bind(id,n.article,at/1000).run();
 const old=globalThis.fetch;globalThis.fetch=async()=>Response.json({ok:true,result:{}});try{
 await newsMenuCallback(e,'ni:l:'+id,80,10);await newsMenuCallback(e,'ni:l:'+id,80,10);
 const initial=(await interestReportData(e)).snapshots;assert.equal(initial.length,1);assert.equal(initial[0].result_choice,'like');assert.equal(JSON.parse(initial[0].decision).route,'instant');
 await e.DB.prepare("UPDATE news_candidates SET route='archive',rule_version='changed' WHERE id=?").bind(n.id).run();
 await newsMenuCallback(e,'ni:d:'+id,80,11);await newsMenuCallback(e,'ni:l:'+id,80,9);await newsMenuCallback(e,'ni:d:'+id,80,12);
 const data=await interestReportData(e);assert.equal(data.records[0].choice,null);assert.equal(data.snapshots.length,3);assert.equal(data.snapshots[0].decision,initial[0].decision);assert.equal(JSON.parse(data.snapshots[1].decision).rule_version,'changed');assert.equal(data.snapshots[2].result_choice,null);
 await e.DB.prepare('DELETE FROM news_candidates').run();const txt=formatInterestReport(await interestReportData(e),at);assert.match(txt,/Mevcut rota: Kayıt yok/);assert.match(txt,/"rule_version":"changed"/);assert.match(txt,/Aselsan/);assert.equal((await e.DB.prepare('SELECT COUNT(*) n FROM x_posts').first<any>()).n,0);
 }finally{globalThis.fetch=old;}
});
test('populated legacy migration preserves votes and detailed feedback without inventing old decisions',async()=>{
 const old=schema.slice(0,schema.indexOf('-- Minimal editor audit metadata')),DB=await localDatabase(':memory:',old);await DB.prepare("INSERT INTO news_interests VALUES('owner','missing',NULL,'s','like',1,10)").run();await DB.prepare("INSERT INTO news_feedback VALUES(4,'old','repeat',10)").run();
 // Run the real additive migration twice, like local schema startup.
 const {DatabaseSync}=await import('node:sqlite');const raw=new DatabaseSync(':memory:');raw.exec(old);raw.exec("INSERT INTO news_interests VALUES('owner','missing',NULL,'s','like',1,10)");const migration=await readFile('migrations/0005_news_interest_evidence.sql','utf8');raw.exec(migration);raw.exec(migration);assert.equal(raw.prepare('SELECT choice FROM news_interests').get()!.choice,'like');assert.equal(raw.prepare('SELECT COUNT(*) n FROM news_interest_context').get()!.n,1);assert.equal(raw.prepare('SELECT COUNT(*) n FROM news_interest_snapshots').get()!.n,0);raw.close();
 const data=await interestReportData({DB,TELEGRAM_USER_ID:'owner'});assert.equal(data.records.length,1);assert.equal(data.snapshots.length,0);
});
