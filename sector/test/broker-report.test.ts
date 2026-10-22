import test from 'node:test';import assert from 'node:assert/strict';import {brokerReport} from '../src/broker-report';import {draftCard} from '../src/card';import type {Document} from '../src/types';
const text='En Çok Net Alış Yapanlar\n'+Array.from({length:5},(_,i)=>`${i+1}. Alıcı ${i} → +12,34 milyon TL`).join('\n')+'\nEn Çok Net Satış Yapanlar\n'+Array.from({length:5},(_,i)=>`${i+1}. Satıcı ${i} → -2,38 milyar TL`).join('\n');
const doc={source_id:'manual-input',url:'https://t.me/ucretsizderinlikbot',market_data:{kind:'broker_flow'},passages:[{id:'market_units',text}]} as Document;
test('broker command preserves signs, institutions and all five rows per side without model rewriting',()=>{const r=brokerReport([doc]);assert.equal(r.draft.card_data!.buy!.length,5);assert.equal(r.draft.card_data!.sell![0].value,'-2,38 milyar TL');assert.equal(r.draft.claims[0].evidence[0].quote,text);assert(draftCard(r.draft).includes('Satıcı 4'));});
test('incomplete broker reply cannot create a partial table',()=>{assert.throws(()=>brokerReport([{...doc,passages:[{id:'market_units',text:text.replace('5. Satıcı 4','Diğer')}]}]),/incomplete/);});

test('undated broker reply persists and retries once through the delivery ledger',async()=>{
 const {saveReport}=await import('../src/kap-report-save');const {localDatabase}=await import('../src/local-adapters');const {readFile}=await import('node:fs/promises');
 const env={DB:await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8')),MEDIA:{put:async()=>{}},RENDER_REPORT:async()=>new Uint8Array([1])} as unknown as import('../src/types').Env;
 await env.DB.prepare("INSERT INTO manual_requests(update_id,message_id,kind,input,created_at) VALUES(1,2,'bot_query','{}',1)").run();
 const result=brokerReport([{...doc,title:'Kurum işlemleri',source_name:'Kaynak bot',published_at:null}]);
 await saveReport(env,{update_id:1,message_id:2},result);await saveReport(env,{update_id:1,message_id:2},result);
 assert.equal((await env.DB.prepare('SELECT COUNT(*) n FROM drafts').first<{n:number}>())!.n,1);
 assert.equal((await env.DB.prepare('SELECT state FROM manual_requests').first<{state:string}>())!.state,'model_queued');
 assert.equal((await env.DB.prepare('SELECT delivery_state FROM drafts').first<{delivery_state:string}>())!.delivery_state,'waiting');
 assert.equal(JSON.parse((await env.DB.prepare('SELECT documents FROM drafts').first<{documents:string}>())!.documents)[0].published_at,null);
});
