import {DOMParser} from 'linkedom';
import {SaxesParser} from 'saxes';
import {normalizeUrl,stripHtml} from './utils/text';
import {safeUrl} from './network';
import type {Source,Item} from './types';
export function sourceDate(value:string):string|null {
  const months:Record<string,string>={'Oca':'Jan','Şub':'Feb','Nis':'Apr','Haz':'Jun','Tem':'Jul','Ağu':'Aug','Eyl':'Sep','Eki':'Oct','Kas':'Nov','Ara':'Dec'};
  let v=value.replace(/(?<!\p{L})(?:Oca|Şub|Nis|Haz|Tem|Ağu|Eyl|Eki|Kas|Ara)(?!\p{L})/gu,m=>months[m]);
  if(/^\d{1,2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2}$/.test(v))v+=' +0300';
  const t=Date.parse(v);return Number.isFinite(t)?new Date(t).toISOString():null;
}
export function parseFeed(xml:string,source:Source):Item[] {
  if(/<!DOCTYPE|<!ENTITY/i.test(xml))throw new Error('unsafe_xml');
  const strict=new SaxesParser({xmlns:true});strict.write(xml).close();
  const doc=new DOMParser().parseFromString(xml,'text/xml');
  if(!['rss','feed','rdf:rdf'].includes(doc.documentElement?.tagName.toLowerCase()))throw new Error('not_a_feed');
  const blocks=[...doc.querySelectorAll('item,entry')];
  if(!blocks.length)throw new Error('empty_feed');
  return blocks.slice(0,100).flatMap(b=>{
    const text=(name:string)=>b.querySelector(name)?.textContent?.trim()??'';
    const link=[...b.querySelectorAll('link')].find(l=>!l.getAttribute('rel')||l.getAttribute('rel')==='alternate');
    const raw=link?.getAttribute('href')||link?.textContent?.trim();
    if(!raw||!text('title'))return [];
    try {
     const target=new URL(raw,source.url);
     // Some official feeds still advertise their own HTTPS-capable pages as HTTP.
     if(target.protocol==='http:'&&source.allowed_hosts.includes(target.hostname))target.protocol='https:';
     return [{title:stripHtml(text('title')),url:normalizeUrl(safeUrl(target.href,source.allowed_hosts)),summary:stripHtml(text('description')||text('summary')||text('content')),published_at:sourceDate(text('pubDate')||text('published')||text('updated')||text('dc\\:date'))}];}
    catch{return [];}
  });
}
