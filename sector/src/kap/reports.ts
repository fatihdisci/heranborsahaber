import {normalize,type Disclosure,type Indices,type fullText} from './parser';
import type {Document,Draft} from '../types';
export const istanbulDay=(at:number)=>new Date(at+10800000).toISOString().slice(0,10);
const clean=(s:string)=>s.replace(/[|\s]+$/g,'').trim();
export interface Purchase {ticker:string;day:string;units:string;program:string;priceMicros?:string;}
// Thousandths of a trading unit, avoiding floating point sums and rounding.
export function quantity(s:string):bigint {
 s=clean(s);if(!/^(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d{1,3})?$/.test(s))throw Error('kap_report_quantity');
 const [a,b='']=s.replace(/\./g,'').split(',');return BigInt(a)*1000n+BigInt(b.padEnd(3,'0'));
}
export function formatQuantity(s:string):string {const n=BigInt(s),a=(n/1000n).toString().replace(/\B(?=(\d{3})+(?!\d))/g,'.'),b=(n%1000n).toString().padStart(3,'0').replace(/0+$/,'');return a+(b?','+b:'');}
export function purchases(page:ReturnType<typeof fullText>):Purchase[]{
 if(!/PAYLARIN GERI ALINMASINA/.test(normalize(page.disclosure.title)))throw Error('kap_report_not_buyback');
 const board=page.labels.find(r=>normalize(clean(r.label))==='YONETIM KURULU KARAR TARIHI');
 if(!board||!/^\d{2}\.\d{2}\.\d{4}$/.test(clean(board.value)))throw Error('kap_report_program_missing');
 const program=clean(board.value),out:Purchase[]=[];let found=false;
 for(const raw of page.tables){const table=raw.map(r=>r.map(clean));
  const h=table.findIndex(r=>r.includes('İşlem Tarihi')&&r.some(c=>/^İşleme Konu Payların Nominal Tutarı \(TL\)$/iu.test(c)));if(h<0)continue;
  found=true;const header=table[h],date=header.indexOf('İşlem Tarihi'),amount=header.findIndex(c=>/^İşleme Konu Payların Nominal Tutarı \(TL\)$/iu.test(c)),stock=header.indexOf('İşleme Konu Pay');
  if(stock<0)throw Error('kap_report_stock_missing');
  for(const row of table.slice(h+1)){if(row.every(c=>!c))continue;if(row.length!==header.length)throw Error('kap_report_row_invalid');
   const m=row[stock].match(/\b([A-Z][A-Z0-9]{3,4}),\s*TR[A-Z0-9]{10}\b/);const dt=row[date].match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
   if(!m||m[1]==='ISKUR'||!dt)throw Error('kap_report_row_invalid');
   const day=`${dt[3]}-${dt[2]}-${dt[1]}`;if(new Date(day+'T00:00:00Z').toISOString().slice(0,10)!==day)throw Error('kap_report_date');
   const priceCol=header.findIndex(c=>/^(ISLEM FIYATI|ORTALAMA ALIM FIYATI) \(TL(?:\/ADET)?\)$/.test(normalize(c)));
   let priceMicros:string|undefined;
   if(priceCol>=0&&row[priceCol]){const v=row[priceCol].replace(/\./g,'');if(!/^\d+(?:,\d{1,6})?$/.test(v))throw Error('kap_report_price');const [a,b='']=v.split(',');const n=BigInt(a)*1000000n+BigInt(b.padEnd(6,'0'));if(n<=0n)throw Error('kap_report_price');priceMicros=n.toString();}
   out.push({ticker:m[1],day,units:quantity(row[amount]).toString(),program,priceMicros});
  }
 }
 if(!found)throw Error('kap_report_table_missing');return out;
}
export interface ReportRecord {disclosure:Disclosure;purchases?:Purchase[];error?:string;}
export function report(kind:'circuit'|'buyback',records:ReportRecord[],indices:Indices|null,at:number,coverage:string):{draft:Draft;documents:Document[]}{
 const day=istanbulDay(at),time=new Date(at).toLocaleTimeString('tr-TR',{timeZone:'Europe/Istanbul',hour:'2-digit',minute:'2-digit'});
 const relevant=records.filter(r=>istanbulDay(Date.parse(r.disclosure.publishedAt))===day&&Date.parse(r.disclosure.publishedAt)<=at&&(kind==='circuit'?normalize(r.disclosure.title+' '+r.disclosure.summary).includes('DEVRE KESICI'):/PAYLARIN GERI ALINMASINA/.test(normalize(r.disclosure.title))));
 const unique=[...new Map(relevant.map(r=>[r.disclosure.id,r])).values()];
 const replaced=new Set(unique.map(r=>r.disclosure.relatedOid).filter(Boolean));
 const current=unique.filter(r=>!r.disclosure.oid||!replaced.has(r.disclosure.oid));
 const rows:{label:string;value:string}[]=[],parts:string[]=[];
 let heading='',footer='KAP kayıtları • '+day+' '+time+' itibarıyla';
 if(kind==='circuit'){
  const counts=new Map<string,number>();for(const r of current)for(const code of new Set(r.disclosure.subjectCodes))counts.set(code,(counts.get(code)??0)+1);
  heading=`Devre kesici raporu: ${current.length} bildirim`;
  parts.push(`${day} saat ${time} itibarıyla kaydedilen ${current.length} devre kesici bildirimi, ${counts.size} farklı hisseyi kapsıyor.`);
  const fresh=indices&&indices.bist50?.length===50&&Math.abs(at-Date.parse(indices.checkedAt))<36*3600000;
  const tier=(c:string)=>fresh?(indices!.bist30.includes(c)?30:indices!.bist50?.includes(c)?50:indices!.bist100.includes(c)?100:999):999;
  const sorted=[...counts].sort((a,b)=>tier(a[0])-tier(b[0])||b[1]-a[1]||a[0].localeCompare(b[0]));
  for(const t of [30,50,100]){const members=sorted.filter(([c])=>tier(c)===t);if(members.length)parts.push(`BIST ${t}${t>30?' (önceki gruplar hariç)':''}: `+members.slice(0,5).map(([c,n])=>`#${c} (${n})`).join(', ')+(members.length>5?` ve ${members.length-5} hisse`:'')+'.');}
  const repeats=sorted.filter(([,n])=>n>1);if(repeats.length)parts.push('Tekrarlayanlar: '+repeats.slice(0,8).map(([c,n])=>`#${c} ${n} kez`).join(', ')+(repeats.length>8?` ve ${repeats.length-8} hisse`:'')+'.');
  for(const [c,n] of sorted)rows.push({label:'#'+c,value:`${n} bildirim${tier(c)<999?' · BIST '+tier(c):''}`});
  if(!fresh)parts.push('Güncel endeks üyeliği doğrulanamadığından endeks ayrımı gösterilmedi.');
 }else{
  const failed=current.filter(r=>!r.purchases||r.error).length;
  // Each programme table is a snapshot. Later disclosures replace earlier
  // tables for that issuer/programme; identical transactions within a table
  // remain separate genuine trades, never collapsed by amount/date.
  const blocked=new Set(current.filter(r=>!r.purchases||r.error).map(r=>r.disclosure.issuerCode??r.disclosure.company));
  const snapshots=new Map<string,{id:number;rows:Purchase[]}>();
  for(const r of current.sort((a,b)=>a.disclosure.id-b.disclosure.id)){
   if(!r.purchases||r.error||blocked.has(r.disclosure.issuerCode??r.disclosure.company))continue;
   const groups=new Map<string,Purchase[]>();for(const p of r.purchases){const key=(r.disclosure.issuerCode??r.disclosure.company)+':'+p.program+':'+p.ticker;groups.set(key,[...(groups.get(key)??[]),p]);}
   for(const [key,values] of groups)snapshots.set(key,{id:r.disclosure.id,rows:values});
  }
  const sums=new Map<string,bigint>();for(const snap of snapshots.values())for(const p of snap.rows)if(p.day===day)sums.set(p.ticker,(sums.get(p.ticker)??0n)+BigInt(p.units));
  const ranked=[...sums].filter(([,n])=>n>0n).sort((a,b)=>a[1]===b[1]?a[0].localeCompare(b[0]):a[1]>b[1]?-1:1);
  heading=failed?'Pay geri alım raporu (kısmi)':`Pay geri alım raporu: ${ranked.length} hisse`;
  parts.push(`${day} saat ${time} itibarıyla ${unique.length} KAP bildirimi kaydedildi. Düzeltmeler sonrası ${current.length} kayıt; bugüne ait doğrulanmış alım bulunan ${ranked.length} hisse.`);
  for(const [c,n] of ranked.slice(0,10)){rows.push({label:'#'+c,value:formatQuantity(n.toString())+' lot'});parts.push(`#${c}: ${formatQuantity(n.toString())} lot`);}
  if(failed)parts.push(`${failed} bildirimin işlem miktarı henüz doğrulanamadı; sıralama eksiktir.`);
  footer='Yalnızca KAP’ta yer alan pay geri alımı bildirimleri esas alınmıştır. Farklılık gösterebilir.';
 }
 if(coverage)parts.push(coverage);
 let body=parts.join('\n\n');
 if(body.length>850){const kept=[parts[0]];for(const part of parts.slice(1,-1))if(kept.join('\n\n').length+part.length<650)kept.push(part);kept.push('Ayrıntılı hisse dağılımı görseldedir.',parts.at(-1)!);body=kept.join('\n\n');}
 const title='📢 '+heading;
 const source='https://www.kap.org.tr/tr/bildirim-sorgu';
 const doc:Document={source_id:'kap-daily-report',source_name:'KAP günlük kayıt raporu',family:'kap-report',official:true,url:source+'#'+kind+'-'+at,title:heading,body,passages:[{id:'computed_report',text:body}],published_at:new Date(at).toISOString(),primary_urls:current.map(r=>r.disclosure.url),language:'tr'};
 const draft:Draft={headline:title,body,hashtags:['Borsa','BIST'],category:'kap',importance:85,template:'info',card_headline:heading,card_body:day+' • '+time+' itibarıyla',card_data:{report:{rows,footer}},claims:[{text:body,evidence:[{document:0,passage:'computed_report',quote:body}]}],entities:[],event_key:kind+'-'+at,uncertainties:[],source_notes:[]};
 return {draft,documents:[doc]};
}
