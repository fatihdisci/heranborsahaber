import {report,istanbulDay,formatQuantity,type ReportRecord,type Purchase} from './kap/reports';
import {normalize,type Indices} from './kap/parser';
export function generalBuyback(_kind:string,records:ReportRecord[],indices:Indices|null,at:number,coverage:string){
 const result=report('buyback',records,indices,at,coverage),day=istanbulDay(at),time=new Date(at).toLocaleTimeString('tr-TR',{timeZone:'Europe/Istanbul',hour:'2-digit',minute:'2-digit'});
 const unique=[...new Map(records.filter(r=>istanbulDay(Date.parse(r.disclosure.publishedAt))===day&&Date.parse(r.disclosure.publishedAt)<=at&&/PAYLARIN GERI ALINMASINA/.test(normalize(r.disclosure.title))).map(r=>[r.disclosure.id,r])).values()];
 const replaced=new Set(unique.map(r=>r.disclosure.relatedOid).filter(Boolean)),current=unique.filter(r=>!r.disclosure.oid||!replaced.has(r.disclosure.oid));
 const blocked=new Set(current.filter(r=>!r.purchases||r.error).map(r=>r.disclosure.issuerCode??r.disclosure.company));
 const snapshots=new Map<string,{rows:Purchase[];url:string}>();
 for(const r of current.sort((a,b)=>a.disclosure.id-b.disclosure.id)){
  const issuer=r.disclosure.issuerCode??r.disclosure.company;if(blocked.has(issuer)||!r.purchases)continue;
  const groups=new Map<string,Purchase[]>();for(const p of r.purchases){const key=issuer+':'+p.program+':'+p.ticker;groups.set(key,[...(groups.get(key)??[]),p]);}
  for(const [key,rows] of groups)snapshots.set(key,{rows,url:r.disclosure.url});
 }
 const totals=new Map<string,{lots:bigint;cost:bigint;complete:boolean;urls:Set<string>}>();
 for(const snap of snapshots.values())for(const p of snap.rows)if(p.day===day){
  const n=BigInt(p.units);if(n<=0n)continue;const v=totals.get(p.ticker)??{lots:0n,cost:0n,complete:true,urls:new Set<string>()};
  v.lots+=n;if(p.priceMicros)v.cost+=n*BigInt(p.priceMicros);else v.complete=false;v.urls.add(snap.url);totals.set(p.ticker,v);
 }
 const decimal=(n:bigint,scale:bigint,places:number)=>{const factor=10n**BigInt(places),v=(n*factor+scale/2n)/scale;return (v/factor).toString().replace(/\B(?=(\d{3})+(?!\d))/g,'.')+','+(v%factor).toString().padStart(places,'0');};
 const sorted=[...totals].sort((a,b)=>a[1].complete!==b[1].complete?a[1].complete?-1:1:a[1].cost===b[1].cost?a[0].localeCompare(b[0]):a[1].cost>b[1].cost?-1:1);
 const rows=sorted.map(([ticker,v])=>({ticker,lots:formatQuantity(v.lots.toString()),price:v.complete?decimal(v.cost,v.lots*1000000n,4):'—',amount:v.complete?decimal(v.cost,1000000000n,2):'—',urls:[...v.urls].join(' ')}));
 const missing=blocked.size+sorted.filter(([,v])=>!v.complete).length;
 const general={day,time,partial:/gecikme|eksik|kısmi/iu.test(coverage),companies:rows.length,lots:formatQuantity([...totals.values()].reduce((a,v)=>a+v.lots,0n).toString()),amount:decimal([...totals.values()].filter(v=>v.complete).reduce((a,v)=>a+v.cost,0n),1000000000n,2),missing,rows};
 const d=result.draft;d.headline='📢 Güncel pay geri alımları';d.card_headline='PAY GERİ ALIMLARI';
 d.body=`${day} saat ${time} itibarıyla kayıtlı işlemlerde ${rows.length} farklı hissede toplam ${general.lots} lot geri alım doğrulandı.\n\n${missing?'Verisi eksik şirketler var; tutar toplamı yalnız fiyatı doğrulanan satırları kapsar.':'Toplam işlem tutarı: '+general.amount+' TL.'}\n\n${coverage}\n\nTüm satırlar görselde ve CSV dosyasında. Yalnız KAP kayıtları esas alınmıştır; farklılık gösterebilir.`;
 d.source_notes=[...(d.source_notes??[]),coverage,...(missing?['Eksik/kısmi geri alım verisi: '+missing+' kayıt/şirket; tutar toplamı yalnız fiyatı doğrulanan satırları kapsar.']:[])];
 d.card_data!.report!.general=general;d.claims=[{text:d.body,evidence:[{document:0,passage:'computed_report',quote:d.body}]}];result.documents[0].body=d.body;result.documents[0].passages=[{id:'computed_report',text:d.body}];return result;
}
export function generalCsv(g:NonNullable<NonNullable<import('./types').CardData['report']>['general']>){
 const quote=(s:string)=>'"'+s.replace(/"/g,'""')+'"';
 return '\uFEFF'+[['Hisse','Lot','Ağırlıklı ortalama fiyat (TL)','Tutar (TL)','İşlem günü','Rapor saati (İstanbul)','KAP bağlantıları'],...g.rows.map(r=>[r.ticker,r.lots,r.price,r.amount,g.day,g.time,r.urls])].map(r=>r.map(quote).join(';')).join('\r\n');
}
