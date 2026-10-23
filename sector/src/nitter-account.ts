import {DOMParser} from 'linkedom';
import {SaxesParser} from 'saxes';
import {readPublic} from './network';

// The same public Nitter mirrors already used by the SPK/Fintables readers.
// No X API credentials or authenticated session are involved.
export const NITTER_MIRRORS=['nitter.netbub.com','nitter.meowing.monster','nitter.pp.ua'] as const;
export interface AccountPost {id:string;at:string;url:string;retweet:boolean;}
export interface AccountSnapshot {posts:AccountPost[];hosts:string[];truncated:boolean;}

export function parseAccountRss(xml:string,account='endeks_haber',host?:string):AccountPost[]{
 if(!/^[a-z0-9_]{1,15}$/i.test(account))throw Error('nitter_account_invalid');
 if(/<!DOCTYPE|<!ENTITY/i.test(xml))throw Error('nitter_unsafe_xml');
 new SaxesParser({xmlns:true}).write(xml).close();
 const root=new DOMParser().parseFromString(xml,'text/xml');
 if(root.documentElement.tagName!=='rss'||!new RegExp('@'+account+'(?:$|[^a-z0-9_])','i').test(root.querySelector('channel > title')?.textContent??''))throw Error('nitter_account_mismatch');
 const items=[...root.querySelectorAll('item')];if(!items.length)throw Error('nitter_empty_feed');
 return items.map(item=>{
  const link=item.querySelector('link')?.textContent?.trim()??'';let url:URL;
  try{url=new URL(link);}catch{throw Error('nitter_post_url');}
  if(host&&!NITTER_MIRRORS.includes(host as typeof NITTER_MIRRORS[number]))throw Error('nitter_unregistered_host');
  if(!NITTER_MIRRORS.includes(url.hostname as typeof NITTER_MIRRORS[number]))throw Error('nitter_unregistered_host');
  const m=url.pathname.match(new RegExp('^/'+account+'/status/(\\d+)$','i'));if(!m)throw Error('nitter_post_url');
  const at=Date.parse(item.querySelector('pubDate')?.textContent??'');if(!Number.isFinite(at)||at>Date.now()+300_000)throw Error('nitter_post_date');
  const title=item.querySelector('title')?.textContent??'';
  return {id:m[1],at:new Date(at).toISOString(),url:`https://x.com/${account}/status/${m[1]}`,retweet:/^\s*RT\s+by\s+@/i.test(title)||/^\s*RT\s+@/i.test(title)};
 });
}

export async function fetchAccountPosts(account='endeks_haber',fetcher:typeof fetch=fetch):Promise<AccountSnapshot>{
 const attempts=await Promise.allSettled(NITTER_MIRRORS.map(async host=>{
  const result=await readPublic(`https://${host}/${account}/rss`,[host],{'Cache-Control':'no-cache'},fetcher);
  return {host,posts:parseAccountRss(result.text,account,host)};
 }));
 const feeds=attempts.flatMap(a=>a.status==='fulfilled'?[a.value]:[]);
 if(!feeds.length)throw Error('nitter_all_mirrors_unavailable');
 const map=new Map<string,AccountPost>();for(const f of feeds)for(const post of f.posts)map.set(post.id,post);
 return {posts:[...map.values()].sort((a,b)=>Date.parse(a.at)-Date.parse(b.at)),hosts:feeds.map(f=>f.host),truncated:feeds.some(f=>f.posts.length>=20)};
}

export function istanbulDate(at:number):string{
 const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Istanbul',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(at);
 const get=(type:string)=>parts.find(p=>p.type===type)?.value??'';
 return `${get('year')}-${get('month')}-${get('day')}`;
}

export function buildAccountReport(day:string,posts:AccountPost[],health:{ok:boolean;hosts?:string[];truncated?:boolean;stale?:boolean;coverage?:string}):string{
 const own=posts.filter(p=>!p.retweet).sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
 const times=own.map(p=>new Date(p.at).toLocaleTimeString('tr-TR',{timeZone:'Europe/Istanbul',hour:'2-digit',minute:'2-digit'}));
 const gaps=own.slice(1).map((p,i)=>(Date.parse(p.at)-Date.parse(own[i].at))/60_000);
 const fmt=(n:number)=>n<60?`${Math.round(n)} dk`:`${Math.floor(n/60)} sa ${Math.round(n%60)} dk`;
 const lines=[`📊 Günlük X paylaşım raporu · ${new Date(`${day}T12:00:00+03:00`).toLocaleDateString('tr-TR',{timeZone:'Europe/Istanbul',day:'numeric',month:'long',year:'numeric'})}`];
 if(!health.ok)lines.push('⚠️ Nitter akışına rapor anında erişilemedi; sayı eksik olabilir.');
 lines.push(`Görülen özgün gönderi: ${own.length}${posts.length!==own.length?` · retweet: ${posts.length-own.length}`:''}`);
 if(times.length)lines.push(`Saatler: ${times.join(' · ')}`);
 if(gaps.length){const avg=gaps.reduce((a,b)=>a+b,0)/gaps.length;const sorted=[...gaps].sort((a,b)=>a-b);const median=sorted[Math.floor(sorted.length/2)];
  lines.push(`Aralıklar: ${gaps.map(fmt).join(' · ')}`);
  lines.push(`Analiz: ortalama ${fmt(avg)}, medyan ${fmt(median)}, en kısa ${fmt(Math.min(...gaps))}, en uzun ${fmt(Math.max(...gaps))}.`);
 }else if(!own.length)lines.push('Gönderi bulunamadı; kaynak erişimi doğrulanmadan bu sonuç kesin sıfır kabul edilmemelidir.');
 else lines.push('Tek gönderi görüldü; gün içi paylaşım aralığı hesaplanamadı.');
 if(health.truncated)lines.push('⚠️ RSS aynası 20 kayıt sınırına ulaştı; gün içi gözlemle yakalanmayan eski gönderiler eksik olabilir.');
 if(health.stale)lines.push('⚠️ Nitter akışındaki en yeni gönderi rapor saatinden 6 saatten eski; bugünkü paylaşım sayısı aynanın gecikmesi nedeniyle eksik olabilir.');
 if(health.coverage)lines.push(`Kapsam: ${health.coverage}`);
 if(health.hosts?.length)lines.push(`Kaynak: Nitter (${health.hosts.join(', ')})`);
 return lines.join('\n');
}
