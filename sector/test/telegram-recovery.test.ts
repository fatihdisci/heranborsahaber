import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {localDatabase} from '../src/local-adapters';
import worker from '../src/worker';
import type {Env} from '../src/types';
async function fixture(){return {DB:await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8')),MODE:'telegram_review',TELEGRAM_BOT_TOKEN:'123:test',TELEGRAM_VERIFIED_BOT_ID:'123',TELEGRAM_USER_ID:'1',TELEGRAM_CHAT_ID:'1',TELEGRAM_WEBHOOK_SECRET:'test'} as Env;}
const update=(id:number,text='/start source_50')=>({update_id:id,message:{message_id:id,from:{id:1},chat:{id:1,type:'private'},text}});
const invoke=(env:Env,value:unknown)=>worker.fetch(new Request('https://local/telegram/webhook',{method:'POST',headers:{'x-telegram-bot-api-secret-token':'test'},body:JSON.stringify(value)}),env,{waitUntil:()=>{}} as unknown as ExecutionContext);
test('deleted source copy is a permanent update failure, not an opaque malformed update',async()=>{
 const env=await fixture(),old=globalThis.fetch;globalThis.fetch=async()=>Response.json({ok:false,error_code:400,description:'Bad Request: message to copy not found'},{status:400});
 try{await env.DB.prepare("INSERT INTO manual_requests(update_id,message_id,kind,input,created_at) VALUES(1,50,'text','{}',1)").run();assert.equal((await (await invoke(env,update(2))).json() as any).failure,'permanent');}finally{globalThis.fetch=old;}
});
import {saveTelegramUpdates,processTelegramUpdates} from '../src/telegram-inbox';
import {telegram} from '../src/telegram';
test('deleted source cannot block the next update; offset acknowledges durable intake and terminal payloads are removed',async()=>{
 const env=await fixture(),old=globalThis.fetch;const methods:string[]=[];
 globalThis.fetch=async(url)=>{const method=String(url).split('/').pop()!;methods.push(method);return method==='copyMessage'?Response.json({ok:false,error_code:400},{status:400}):Response.json({ok:true,result:{message_id:90}});};
 try{
  await env.DB.prepare("INSERT INTO manual_requests(update_id,message_id,kind,input,created_at) VALUES(1,50,'text','{}',1)").run();
  const updates=[update(2),update(3,'/help')];await saveTelegramUpdates(env,updates,100);await saveTelegramUpdates(env,updates,100);
  assert.equal((await env.DB.prepare("SELECT value FROM system_state WHERE key='telegram_offset'").first<any>()).value,'4');
  await processTelegramUpdates(env,u=>invoke(env,u),100);await processTelegramUpdates(env,u=>invoke(env,u),200);
  assert.deepEqual(methods,['copyMessage','sendMessage']);
  assert.deepEqual((await env.DB.prepare('SELECT state,payload FROM telegram_updates ORDER BY update_id').all<any>()).results?.map(r=>({...r})),[{state:'failed',payload:'{}'},{state:'complete',payload:'{}'}]);
 }finally{globalThis.fetch=old;}
});
test('explicit rejection retries with a cap while later updates continue; network ambiguity is never resent',async()=>{
 const env=await fixture(),old=globalThis.fetch;let calls=0;
 globalThis.fetch=async()=>{calls++;return Response.json({ok:false,error_code:429,parameters:{retry_after:1}},{status:429});};
 try{
  await saveTelegramUpdates(env,[update(10,'/help')],100);
  for(const t of [100,130,190,500])await processTelegramUpdates(env,u=>invoke(env,u),t);
  assert.equal(calls,3);assert.equal((await env.DB.prepare('SELECT state FROM telegram_updates').first<any>()).state,'failed');
  globalThis.fetch=async()=>{calls++;throw Error('socket reset after request');};
  await saveTelegramUpdates(env,[update(11,'/help')],600);await processTelegramUpdates(env,u=>invoke(env,u),600);await processTelegramUpdates(env,u=>invoke(env,u),1000);
  assert.equal(calls,4);assert.equal((await env.DB.prepare('SELECT state FROM telegram_updates WHERE update_id=11').first<any>()).state,'uncertain');
 }finally{globalThis.fetch=old;}
});
test('stored effect receipts prevent duplicate sends after handler/database failure or restart',async()=>{
 const env=await fixture(),old=globalThis.fetch;let calls=0;
 globalThis.fetch=async()=>{calls++;return Response.json({ok:true,result:{message_id:90}});};
 try{
  await saveTelegramUpdates(env,[update(12,'/help')],100);
  await processTelegramUpdates(env,async u=>{await invoke(env,u);throw Error('after send');},100);
  await processTelegramUpdates(env,u=>invoke(env,u),200);assert.equal(calls,1);
  assert.equal((await env.DB.prepare('SELECT state FROM telegram_updates').first<any>()).state,'complete');
  const contextual={...env,TELEGRAM_UPDATE_ID:13};
  const form=new URLSearchParams({chat_id:'1',text:'same'});
  globalThis.fetch=async()=>{calls++;throw Error('timeout');};
  await assert.rejects(()=>telegram(contextual,'sendMessage',form));await assert.rejects(()=>telegram(contextual,'sendMessage',form));assert.equal(calls,2);
 }finally{globalThis.fetch=old;}
});
test('idempotent edit can recover from a timeout and message-not-modified; no new message is sent',async()=>{
 const env={...await fixture(),TELEGRAM_UPDATE_ID:15},old=globalThis.fetch;let calls=0;
 globalThis.fetch=async()=>{calls++;if(calls===1)throw Error('timeout');return Response.json({ok:false,error_code:400,description:'Bad Request: message is not modified: same content'},{status:400});};
 try{const body=new URLSearchParams({chat_id:'1',message_id:'100',text:'same'});await assert.rejects(()=>telegram(env,'editMessageText',body));assert.equal((await telegram(env,'editMessageText',body)).message_id,100);assert.equal(calls,2);}finally{globalThis.fetch=old;}
});
