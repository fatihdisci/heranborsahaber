import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {localDatabase} from '../src/local-adapters';
import {keyboard} from '../src/telegram';
import {postText} from '../src/editorial';
import worker from '../src/worker';
import type {Env,Document,Draft} from '../src/types';
const id='00000000-0000-4000-8000-000000000000';
const docs=[{url:'https://example.com/news'}] as Document[];
const draft={headline:'📢 Şirket yatırımını açıkladı',body:'A < B & C `metin` '.repeat(25),hashtags:['#Borsa','#BIST']} as Draft;
async function fixture(){
 const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8'));
 await DB.prepare('INSERT INTO drafts(id,event_key,fingerprint,content,documents,verification,created_at,expires_at,message_id,media_key) VALUES(?,?,?,?,?,?,?,?,?,?)').bind(id,'e','f',JSON.stringify(draft),JSON.stringify(docs),'official',1,2,100,'draft.png').run();
 return {DB,MODE:'telegram_review',TELEGRAM_USER_ID:'1',TELEGRAM_CHAT_ID:'1',TELEGRAM_BOT_TOKEN:'123:test',TELEGRAM_VERIFIED_BOT_ID:'123',TELEGRAM_WEBHOOK_SECRET:'test',MEDIA:{get:async()=>({arrayBuffer:async()=>new Uint8Array([137,80,78,71]).buffer})}} as unknown as Env;
}
async function press(env:Env,kind='text',update=1,user=1,revision=1,message=100){
 return worker.fetch(new Request('https://local/telegram/webhook',{method:'POST',headers:{'x-telegram-bot-api-secret-token':'test'},body:JSON.stringify({update_id:update,callback_query:{id:'callback'+update,data:`asset:${kind}:${id}:${revision}`,from:{id:user},message:{message_id:message,chat:{id:1,type:'private'}}}})}),env,{waitUntil:()=>{}} as unknown as ExecutionContext);
}
test('native copy preserves 256 characters; longer captions never truncate',()=>{
 assert.deepEqual(keyboard(id,1,docs,'a'.repeat(256)).inline_keyboard[1][0],{text:'Tweet’i kopyala',copy_text:{text:'a'.repeat(256)}});
 const long=keyboard(id,2,docs,'a'.repeat(257)).inline_keyboard[1];
 assert.equal('copy_text' in long[0],false);
 assert.equal(long.length,1);
 assert(!JSON.stringify(keyboard(id,2,docs,'a'.repeat(257))).includes('Görseli al'));
 assert.equal((long[0] as {callback_data:string}).callback_data,`asset:text:${id}:2`);
 for(const button of long)assert(Buffer.byteLength((button as {callback_data:string}).callback_data)<=64);
});
test('copy sends exact text with UTF-16 entity, without AI or duplicate delivery',async()=>{
 const env=await fixture(),original=globalThis.fetch,calls:{url:string;body:URLSearchParams}[]=[];
 globalThis.fetch=async(url,init)=>{calls.push({url:String(url),body:init!.body as URLSearchParams});return Response.json({ok:true,result:{message_id:101}});};
 try{
  await press(env);await press(env);
  const messages=calls.filter(c=>c.url.endsWith('/sendMessage'));assert.equal(messages.length,1);
  const text=postText(draft);assert.equal(messages[0].body.get('text'),text);
  assert.deepEqual(JSON.parse(messages[0].body.get('entities')!),[{type:'pre',offset:0,length:text.length}]);
  assert.equal(messages[0].body.has('parse_mode'),false);
  assert.equal((await env.DB.prepare('SELECT state FROM drafts').first<{state:string}>())!.state,'pending');
  assert.equal((await env.DB.prepare('SELECT count(*) AS n FROM model_jobs').first<{n:number}>())!.n,0);
 }finally{globalThis.fetch=original;}
});
test('image uploads original PNG; unauthorized and stale buttons cannot access assets',async()=>{
 const env=await fixture(),original=globalThis.fetch,calls:{url:string;body:FormData}[]=[];
 globalThis.fetch=async(url,init)=>{calls.push({url:String(url),body:init!.body as FormData});return Response.json({ok:true,result:{message_id:101}});};
 try{
  await press(env,'image',1,2);assert.equal(calls.length,0);
  await press(env,'image',2,1,2);await press(env,'image',3,1,1,999);
  assert.equal(calls.filter(c=>c.url.endsWith('/sendDocument')).length,0);
  await press(env,'image',4);
  const files=calls.filter(c=>c.url.endsWith('/sendDocument'));assert.equal(files.length,1);
  const file=files[0].body.get('document') as File;assert.equal(file.type,'image/png');
  assert.deepEqual([...new Uint8Array(await file.arrayBuffer())],[137,80,78,71]);
 }finally{globalThis.fetch=original;}
});
test('missing image reports failure without clipboard success or automatic retry',async()=>{
 const env=await fixture();env.MEDIA={get:async()=>null} as unknown as R2Bucket;
 const original=globalThis.fetch,calls:{url:string;body:URLSearchParams}[]=[];
 globalThis.fetch=async(url,init)=>{calls.push({url:String(url),body:init!.body as URLSearchParams});return Response.json({ok:true,result:{message_id:101}});};
 try{
  await press(env,'image');assert(!calls.some(c=>c.url.endsWith('/sendDocument')));
  assert.match(calls.find(c=>c.url.endsWith('/sendMessage'))!.body.get('text')!,/doğrulanamadı/);
  assert(!calls.some(c=>/kopyalandı/i.test(c.body.get('text')??'')));
 }finally{globalThis.fetch=original;}
});
