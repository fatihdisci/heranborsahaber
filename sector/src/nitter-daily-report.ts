import type {Env} from './types';
import {telegram,TelegramError} from './telegram';
import {buildAccountReport,fetchAccountPosts,istanbulDate,type AccountPost,type AccountSnapshot} from './nitter-account';

type Loader=(account:string)=>Promise<AccountSnapshot>;
type Sender=(text:string)=>Promise<unknown>;
type DailyState={day:string;posts:AccountPost[];first_poll_at:number;last_poll_at:number;last_hosts:string[];last_feed_latest_at:string|null;truncated:boolean;coverage_gap:boolean;};
const account='endeks_haber';
const getState=async<T>(env:Env,key:string):Promise<T|null>=>{const row=await env.DB.prepare('SELECT value FROM system_state WHERE key=?').bind(key).first<{value:string}>();if(!row)return null;try{return JSON.parse(row.value) as T;}catch{return null;}};
const putState=(env:Env,key:string,value:unknown)=>env.DB.prepare('INSERT INTO system_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value').bind(key,JSON.stringify(value)).run();
export const dailyAccountKey=(day:string)=>`nitter_account_posts:${day}`;
export const dailyReportKey=(day:string)=>`nitter_daily_report:${day}`;
export function dailyReportDue(now:number):boolean{
 const day=istanbulDate(now);return now>=Date.parse(`${day}T23:00:00+03:00`);
}

/** Polls the public Nitter mirrors and merges IDs so the RSS latest-20 window cannot erase earlier observations. */
export async function observeAccountPosts(env:Env,now=Date.now(),load:Loader=account=>fetchAccountPosts(account)){
 const day=istanbulDate(now),key=dailyAccountKey(day),previous=await getState<DailyState>(env,key);
 try{
  const snap=await load(account);const today=snap.posts.filter(p=>istanbulDate(Date.parse(p.at))===day&&Date.parse(p.at)<=now+300_000);
  const posts=new Map((previous?.posts??[]).map(p=>[p.id,p]));for(const p of today)posts.set(p.id,p);
  const value:DailyState={day,posts:[...posts.values()].sort((a,b)=>Date.parse(a.at)-Date.parse(b.at)),first_poll_at:previous?.first_poll_at??now,last_poll_at:now,last_hosts:snap.hosts,last_feed_latest_at:snap.posts.at(-1)?.at??previous?.last_feed_latest_at??null,truncated:!!previous?.truncated||today.length>=20,coverage_gap:!!previous?.coverage_gap};
  await putState(env,key,value);
  await putState(env,'nitter_account_health',{ok:true,at:now,host:snap.hosts,feed_count:snap.posts.length,today_count:value.posts.length,failures:0,truncated:value.truncated});
  return {value,ok:true as const,hosts:snap.hosts,latestAt:snap.posts.at(-1)?.at??null};
 }catch(e){
  const health=await getState<any>(env,'nitter_account_health');
  await putState(env,'nitter_account_health',{ok:false,at:health?.at??null,last_attempt:now,failures:(health?.failures??0)+1,code:e instanceof Error?e.message:'nitter_fetch_failed'});
  return {value:previous,ok:false as const,hosts:previous?.last_hosts??[],latestAt:previous?.last_feed_latest_at??null};
 }
}

export async function sendDailyAccountReport(env:Env,now=Date.now(),load:Loader=account=>fetchAccountPosts(account),send:Sender=async text=>telegram(env,'sendMessage',new URLSearchParams({chat_id:env.TELEGRAM_CHAT_ID!,text}))){
 if(!dailyReportDue(now))return {state:'not_due' as const};
 const day=istanbulDate(now),key=dailyReportKey(day),existing=await getState<any>(env,key);
 if(existing?.state==='sent'||existing?.state==='uncertain'||existing?.state==='failed')return {state:existing.state as string};
 if(existing?.state==='sending'){
  if(now-Number(existing.started_at)<120_000)return {state:'sending' as const};
  await putState(env,key,{...existing,state:'uncertain',updated_at:now,error:'send_outcome_unknown_after_restart'});return {state:'uncertain' as const};
 }
 if(Number(existing?.next_retry_at??0)>now)return {state:'retry_wait' as const};
 const observed=await observeAccountPosts(env,now,load);
 const daily=observed.value;
 const latestAt=observed.latestAt??daily?.last_feed_latest_at??null;
 const health={ok:observed.ok,hosts:observed.hosts,truncated:daily?.truncated??false,stale:!!latestAt&&now-Date.parse(latestAt)>6*3600_000,coverage:daily?`İlk gözlem ${new Date(daily.first_poll_at).toLocaleTimeString('tr-TR',{timeZone:'Europe/Istanbul',hour:'2-digit',minute:'2-digit'})}; bu zamandan önceki olası kesintiler kapsama dahil olmayabilir.`:'Günlük gözlem kaydı yok.'};
 const text=buildAccountReport(day,daily?.posts??[],health);
 await putState(env,key,{day,state:'sending',started_at:now,text});
 try{
  const result=await send(text);
  await putState(env,key,{day,state:'sent',sent_at:now,message_id:Number((result as any)?.message_id)||null,text});
  await putState(env,'nitter_daily_report_health',{ok:true,at:now,day,count:daily?.posts.filter(p=>!p.retweet).length??0});
  return {state:'sent' as const,text};
 }catch(e){
  const telegramFailure=e instanceof TelegramError?e.failure:'retryable';
  const state=telegramFailure==='uncertain'?'uncertain':telegramFailure==='permanent'?'failed':'retry';
  await putState(env,key,{day,state,updated_at:now,next_retry_at:state==='retry'?now+60_000:null,error:e instanceof Error?e.message:'telegram_send_failed',text});
  await putState(env,'nitter_daily_report_health',{ok:false,at:now,day,error:e instanceof Error?e.message:'telegram_send_failed',state});
  return {state,text};
 }
}
