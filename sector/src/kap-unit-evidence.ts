import type {Document,Draft} from './types';
// BIST Pay Piyasası Prosedürü 5.1.1: trading units, not a universal
// assertion about the legal denomination of every company's shares.
export function withKapUnitEvidence(documents:Document[]):Document[]{
 return documents.map(d=>{
  const fold=(s:string)=>s.toLocaleLowerCase('tr-TR').replace(/ı/g,'i');
  const issuer=fold(d.title.split(/\s+—\s+/)[0]);
  const issuerPattern=issuer.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  // General disclosures may describe a transaction in the listed issuer's own
  // shares without repeating the exchange name or using a share-deal title.
  const ownShareDeal=issuer!==fold(d.title)&&new RegExp(issuerPattern+"\\s+paylari\\s+ile ilgili",'u').test(fold(d.body))&&/nominal tutarlı\s+(?:alış|alım|satış|satım)/iu.test(d.body)&&/TL\s+fiyat aralığından/iu.test(d.body);
  if(d.source_id!=='kap'||!d.official||!/^https:\/\/www\.kap\.org\.tr\/tr\/Bildirim\/\d+$/.test(d.url)||
   d.equity_codes?.length!==1||d.equity_codes.includes('ISKUR')||
   (!/pay.*(?:geri al|alım|satım)/iu.test(d.title)&&!ownShareDeal)||
   (!/borsa istanbul|borsa[’']?da|bist/u.test(d.body.toLocaleLowerCase('tr-TR').replace(/ı/g,'i'))&&!ownShareDeal))return d;
  const text='Borsa İstanbul pay işlemlerinin işlem birimi: 1 TL nominal = 1 adet pay = 1 lot. Kaynak: https://borsaistanbul.com/files/pay-piyasasi-proseduru.pdf bölüm 5.1.1. Bu eşitlik yalnız bu bildirimin borsada işlem gören pay miktarına uygulanır; fiyat, nakit ödeme, bütçe ve özel şirket payları için uygulanmaz.';
  const extra=d.passages.some(p=>p.id==='bist_units')?[]:[{id:'bist_units',text}];
  // Add explicit equivalences only for nominal-labelled share quantities.
  // Original passages remain untouched and available to the semantic audit.
  for(const p of d.passages){
   if(/(?:_units|^bist_units)$/.test(p.id)||!/[\p{L}]/u.test(p.text)||!/pay/iu.test(p.text)||!/nominal/iu.test(p.text)||/^[\s]*\[/.test(p.text))continue;
   const equivalents=[...p.text.matchAll(/(?:nominal\s+(?:tutar[ıi]|değer[il]?[iı]?)\s*[:=]?\s*)(\d+(?:[.,]\d+)*)\s*TL\b/giu)].map(m=>m[1]);
   // Header-annotated table rows keep units adjacent to their own cell.
   for(const m of p.text.matchAll(/[^|\n]*pay[^|\n]*nominal[^|\n]*:\s*(\d+(?:[.,]\d+)*)\s*TL\b/giu))equivalents.push(m[1]);
   for(const m of p.text.matchAll(/(\d+(?:[.,]\d+)*)\s+TL\s+nominal\s+değerli\s+(?:[A-Z0-9]{4,5}\s+)?(?:[AB]\s+Grubu\s+)?pay/giu))equivalents.push(m[1]);
   for(const m of p.text.matchAll(/(\d+(?:[.,]\d+)*)\s+(?:toplam\s+)?nominal\s+tutarlı\s+(?:alış|alım|satış|satım)/giu))equivalents.push(m[1]);
   if(equivalents.length){const generated={id:p.id+'_units',text:p.text+'\nBIST işlem birimi karşılıkları: '+[...new Set(equivalents)].map(n=>`${n} TL nominal pay miktarı = ${n} adet pay`).join('; ')};if(!d.passages.some(q=>q.id===generated.id&&q.text===generated.text))extra.push(generated);}
  }
  if(!extra.length)return d;
  return {...d,body:d.body+'\n\n'+extra.map(p=>p.text).join('\n\n'),passages:[...d.passages.filter(p=>!extra.some(q=>q.id===p.id)),...extra]};
 });
}

// Use only explicit amount-by-amount equivalences supplied by our KAP reader.
// Quotations remain verbatim. Repaired claims cite the conversion alongside
// their original evidence so the semantic audit still sees every step.
export function repairKapShareWording(draft:Draft,documents:Document[]):Draft {
 if(!draft||typeof draft!=='object')return draft;
 const proof=documents.flatMap((doc,document)=>doc.passages.filter(p=>p.id.endsWith('_units')&&doc.passages.some(p=>p.id==='bist_units')).flatMap(p=>
  [...p.text.matchAll(/(\d+(?:[.,]\d+)*) TL nominal pay miktarı = \1 adet pay/g)].map(m=>({amount:m[1],document,passage:p.id,quote:p.text}))));
 if(!proof.length)return draft;
 const replace=(text:string):string=>{
  if(typeof text!=='string')return text;
  for(const {amount} of proof){
   const n=amount.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),start='(?<![\\d.,])'+n;
   text=text.replace(new RegExp(start+'\\s+TL\\s+nominal(?:\\s+(?:değerli|tutarlı))?(?=\\s+(?:[A-Z0-9]{4,5}\\s+)?(?:[AB]\\s+Grubu\\s+)?pay)','giu'),amount+' adet');
   text=text.replace(new RegExp('payların\\s+(?:toplam\\s+)?nominal\\s+(?:tutarı|değeri)\\s+'+n+'\\s+TL','giu'),'toplam pay adedi '+amount);
   text=text.replace(new RegExp('nominal\\s+(?:tutarı|değeri)\\s+'+n+'\\s+TL','giu'),'pay adedi '+amount);
   text=text.replace(new RegExp(start+'\\s+(?:toplam\\s+)?nominal\\s+tutarlı(?=\\s+(?:alım|alış|satım|satış))','giu'),amount+' adet pay');
  }
  return text.replace(/adet pay (alım|alış) yaptı/giu,'adet pay aldı').replace(/adet pay (satım|satış) yaptı/giu,'adet pay sattı').replace(/adet pay (alım|alış) gerçekleştir/giu,'adet pay alımı gerçekleştir').replace(/adet pay (satım|satış) gerçekleştir/giu,'adet pay satışı gerçekleştir');
 };
 const claims=Array.isArray(draft.claims)?draft.claims.map(c=>{
  const text=replace(c.text);if(text===c.text)return c;
  const evidence=[...c.evidence];
  for(const p of proof)if(new RegExp('(?<![\\d.,])'+p.amount.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?![\\d.,])').test(text)&&c.evidence.some(e=>e.document===p.document&&e.passage+'_units'===p.passage)&&!evidence.some(e=>e.document===p.document&&e.passage===p.passage))evidence.push({document:p.document,passage:p.passage,quote:p.quote});
  return {...c,text,evidence};
 }):draft.claims;
 return {...draft,headline:replace(draft.headline),body:replace(draft.body),card_headline:replace(draft.card_headline),card_body:replace(draft.card_body),claims};
}
