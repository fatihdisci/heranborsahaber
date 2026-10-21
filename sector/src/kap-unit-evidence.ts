import type {Document} from './types';
// BIST Pay Piyasası Prosedürü 5.1.1: trading units, not a universal
// assertion about the legal denomination of every company's shares.
export function withKapUnitEvidence(documents:Document[]):Document[]{
 return documents.map(d=>{
  if(d.source_id!=='kap'||!d.official||!/^https:\/\/www\.kap\.org\.tr\/tr\/Bildirim\/\d+$/.test(d.url)||
   d.equity_codes?.length!==1||d.equity_codes.includes('ISKUR')||
   !/pay.*(?:geri al|alım|satım)/iu.test(d.title)||
   !/borsa istanbul|borsa[’']?da|bist/u.test(d.body.toLocaleLowerCase('tr-TR').replace(/ı/g,'i'))||d.passages.some(p=>p.id==='bist_units'))return d;
  const text='Borsa İstanbul pay işlemlerinin işlem birimi: 1 TL nominal = 1 adet pay = 1 lot. Kaynak: https://borsaistanbul.com/files/pay-piyasasi-proseduru.pdf bölüm 5.1.1. Bu eşitlik yalnız bu bildirimin borsada işlem gören pay miktarına uygulanır; fiyat, nakit ödeme, bütçe ve özel şirket payları için uygulanmaz.';
  const extra=[{id:'bist_units',text}];
  // Add explicit equivalences only for nominal-labelled share quantities.
  // Original passages remain untouched and available to the semantic audit.
  for(const p of d.passages){
   if(!/pay/iu.test(p.text)||!/nominal/iu.test(p.text)||/^[\s]*\[/.test(p.text))continue;
   const equivalents=[...p.text.matchAll(/(?:nominal\s+(?:tutar[ıi]|değer[il]?[iı]?)\s*[:=]?\s*)(\d+(?:[.,]\d+)*)\s*TL\b/giu)].map(m=>m[1]);
   // Header-annotated table rows keep units adjacent to their own cell.
   for(const m of p.text.matchAll(/[^|\n]*pay[^|\n]*nominal[^|\n]*:\s*(\d+(?:[.,]\d+)*)\s*TL\b/giu))equivalents.push(m[1]);
   if(equivalents.length)extra.push({id:p.id+'_units',text:p.text+'\nBIST işlem birimi karşılıkları: '+[...new Set(equivalents)].map(n=>`${n} TL nominal pay miktarı = ${n} adet pay`).join('; ')});
  }
  return {...d,body:d.body+'\n\n'+extra.map(p=>p.text).join('\n\n'),passages:[...d.passages,...extra]};
 });
}
