import {withKapTableEvidence} from './kap-table-evidence';
import type {Document,Draft,CardRow} from './types';
const fold=(s:string)=>s.toLocaleLowerCase('tr-TR').replace(/ı/g,'i');
const escape=(s:string)=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const amount='(\\d+(?:[.,]\\d+)*)';
const main=(d:Document)=>d.source_id==='kap'&&d.official&&/^https:\/\/www\.kap\.org\.tr\/tr\/Bildirim\/\d+$/.test(d.url);
const issuer=(d:Document)=>fold(d.title.split(/\s+—\s+/)[0]);
const shareTitle=(d:Document)=>/pay.*(?:geri al|alım|satım)/iu.test(d.title);
function eligible(d:Document,documents:Document[]):boolean {
 const body=d.body.replace(/\s+/g,' ');
 const related=body.match(/İlgili Şirketler\s*(?:Related Companies\s*)?\|?\s*\[([A-Z][A-Z0-9]{3,4})\]/u)?.[1];
 // A KAP trade row explicitly pairs a security code and its ISIN. This also
 // supports older stored evidence that predates equity_codes metadata.
 const tableCodes=[...new Set(d.passages.filter(p=>/^table\d+row\d+$/.test(p.id)).flatMap(p=>[...p.text.matchAll(/İşleme Konu Pay:\s*(?:[AB] Grubu,\s*)?([A-Z][A-Z0-9]{3,4}),\s*[A-Z]{2}[A-Z0-9]{9}\d\b/gu)].map(m=>m[1])))];
 const codes=d.equity_codes?.length?d.equity_codes:tableCodes.length?tableCodes:related?[related]:[];
 if(d.source_id!=='kap'||!d.official||codes.length!==1||!/^[A-Z][A-Z0-9]{3,4}$/.test(codes[0])||
  /\bISKUR\b/.test(codes.join(' ')+' '+body)||/borsada işlem görmeyen|halka açık olmayan/iu.test(body))return false;
 // General disclosures can describe a listed issuer's own shares without
 // repeating the exchange name. Never borrow that context for another issuer.
 const ownShareDeal=issuer(d)!==fold(d.title)&&new RegExp(escape(issuer(d))+"\\s+paylari\\s+ile ilgili",'u').test(fold(body))&&
  /nominal tutarlı\s+(?:geri\s+)?(?:alış|alım|satış|satım)/iu.test(body)&&/TL\s+fiyat aralığından/iu.test(body);
 const relatedTrade=!!related&&related!=='ISKUR'&&new RegExp('payları(?:\\s*\\('+escape(related)+'\\))?\\s+ile ilgili|paylarında,','iu').test(body)&&/nominal\s+tutarlı\s+(?:pay\s+)?(?:alış|alım|satış|satım)/iu.test(body);
 if(main(d))return (shareTitle(d)||ownShareDeal)&&(/borsa istanbul|borsa[’']?da|bist/u.test(fold(body))||ownShareDeal||tableCodes.length===1||relatedTrade);
 if(!/^https:\/\/www\.kap\.org\.tr\/tr\/api\/file\/download\/[a-f0-9]{32}$/i.test(d.url)||!d.coverage?.complete)return false;
 // MKK's main page often says only "see attachment". Its PDF carries the
 // actual share transaction. Bind it to one matching official disclosure;
 // a security name/amount in an unrelated PDF is not conversion evidence.
 const parents=documents.filter(p=>main(p)&&shareTitle(p)&&p.published_at!==null&&p.published_at===d.published_at&&
  p.equity_codes?.length===1&&p.equity_codes[0]===codes[0]&&issuer(p)===issuer(d));
 if(parents.length!==1)return false;
 const filename=d.title.split(/\s+—\s+/).at(-1)??'';
 return (/bildirime konu borsa şirketi/iu.test(body)||new RegExp('^'+escape(codes[0])+'(?:[_.\\s-]|$)').test(filename))&&
  /payları\s+ile ilgili/iu.test(body)&&/nominal\s+tutarlı\s+(?:pay\s+)?(?:alış|alım|satış|satım)/iu.test(body)&&/TL\s+fiyat(?:\s+aralığından|\s+ile|tan)/iu.test(body);
}
// Exact integral spelling equivalents, never rounded quantities. For example,
// "300 bin" can match a verified 300.000; "1,1 milyon" cannot match 1.135.381.
function amountPattern(n:string):string {
 const aliases=[escape(n),escape(n.replace(/\./g,''))];
 if(/^\d+(?:\.\d{3})*$/.test(n)){
  const value=BigInt(n.replace(/\./g,''));
  if(value>0n)for(const [scale,word] of [[1000n,'bin'],[1000000n,'milyon'],[1000000000n,'milyar']] as const)
   if(value%scale===0n)aliases.push(String(value/scale)+'\\s+'+word);
 }
 return '(?:'+[...new Set(aliases)].join('|')+')';
}
function nominalAmounts(text:string,tableRow:boolean,company:string):string[] {
 const found:string[]=[];
 const name=escape(company).replace(/[ıiİI]/g,'[ıiİI]');
 const patterns=[
  // A share label must qualify the nominal amount. A bond's nominal value in
  // the same paragraph is not a share quantity.
  new RegExp('pay[\\p{L}]*\\s+(?:(?:toplam|gün|başı|sonu)\\s+)*nominal\\s+(?:tutar[ıi]|değer[iı])\\s*[:=]?\\s*'+amount+'\\s*TL\\b','giu'),
  new RegExp(amount+'\\s+(?:TL\\s+)?(?:toplam\\s+)?nominal\\s+(?:değerli|tutarlı)\\s+(?:(?:[A-Z0-9]{4,5}|'+name+')\\s+)?(?:[AB]\\s+Grubu\\s+)?(?:pay|(?:geri\\s+)?(?:alış|alım|satış|satım))','giu'),
  new RegExp(amount+'\\s+TL\\s+(?:toplam\\s+)?nominal\\s+bedelli(?=\\s+\\d+(?:[.,]\\d+)*\\s+TL\\s+tutarında\\s+(?:alış|alım|satış|satım))','giu')
 ];
 if(tableRow)patterns.push(new RegExp('(?:^|[|])[^|]*pay[^|]*nominal[^|]*:\\s*'+amount+'\\s*TL\\b','giu'));
 for(const re of patterns)for(const m of text.matchAll(re))found.push(m[1]);
 return [...new Set(found)];
}
// BIST Pay Piyasası Prosedürü 5.1.1 describes trading units, not the legal
// denomination of private-company shares. Retain original KAP/PDF quotations.
export function withKapUnitEvidence(documents:Document[]):Document[]{
 const annotated=withKapTableEvidence(documents);
 return annotated.map(d=>{
  if(!eligible(d,annotated))return d;
  const text='Borsa İstanbul pay işlemlerinin işlem birimi: 1 TL nominal = 1 adet pay = 1 lot. Kaynak: https://borsaistanbul.com/files/pay-piyasasi-proseduru.pdf bölüm 5.1.1. Bu eşitlik yalnız bu bildirimin borsada işlem gören pay miktarına uygulanır; fiyat, nakit ödeme, bütçe ve özel şirket payları için uygulanmaz.';
  const extra=d.passages.some(p=>p.id==='bist_units')?[]:[{id:'bist_units',text}];
  const remove=new Set<string>();
  for(const p of d.passages){
   if(/(?:_units|^bist_units)$/.test(p.id)||!/pay/iu.test(p.text)||!/nominal/iu.test(p.text)||/^\s*\[/.test(p.text))continue;
   const equivalents=nominalAmounts(p.text.replace(/\s+/g,' '),/^(?:page\d+_)?table\d+row\d+$/.test(p.id),d.title.split(/\s+—\s+/)[0]);
   if(equivalents.length){
    const generated={id:p.id+'_units',text:p.text+'\nBIST işlem birimi karşılıkları: '+equivalents.map(n=>`${n} TL nominal pay miktarı = ${n} adet pay`).join('; ')};
    if(!d.passages.some(q=>q.id===generated.id&&q.text===generated.text))extra.push(generated);
   }else if(d.passages.some(q=>q.id===p.id+'_units'&&q.text.startsWith(p.text+'\nBIST işlem birimi karşılıkları: ')))remove.add(p.id+'_units');
  }
  if(!extra.length&&!remove.size)return d;
  let body=d.body;
  for(const old of d.passages.filter(p=>remove.has(p.id)||extra.some(q=>q.id===p.id)))body=body.replaceAll(old.text,'');
  return {...d,body:[body.trim(),...extra.map(p=>p.text)].filter(Boolean).join('\n\n'),passages:[...d.passages.filter(p=>!remove.has(p.id)&&!extra.some(q=>q.id===p.id)),...extra]};
 });
}

// Only amount-by-amount equivalences supplied by the KAP reader can repair a
// draft. Original evidence remains verbatim; claims also cite the conversion.
export function repairKapShareWording(draft:Draft,documents:Document[]):Draft {
 if(!draft||typeof draft!=='object')return draft;
 const proof=documents.flatMap((doc,document)=>doc.passages.filter(p=>p.id.endsWith('_units')&&doc.passages.some(p=>p.id==='bist_units')).flatMap(p=>
  [...p.text.matchAll(/(\d+(?:[.,]\d+)*) TL nominal pay miktarı = \1 adet pay/g)].map(m=>({amount:m[1],document,passage:p.id,quote:p.text}))));
 if(!proof.length)return draft;
 const amounts=[...new Set(proof.map(p=>p.amount))];
 const replace=(text:string):string=>{
  if(typeof text!=='string')return text;
  for(const n of amounts){
   const exact='(?<![\\d.,])'+amountPattern(n);
   text=text.replace(new RegExp(exact+'\\s+(?:TL\\s+)?(?:toplam\\s+)?nominal(?:\\s+(?:değerli|tutarlı))?(?=\\s+(?:[A-Z0-9]{4,5}\\s+)?(?:[AB]\\s+Grubu\\s+)?pay)','giu'),n+' adet');
   text=text.replace(new RegExp('payların\\s+(?:toplam\\s+)?nominal\\s+(?:tutarı|değeri)\\s+'+amountPattern(n)+'\\s+TL','giu'),'toplam pay adedi '+n);
   text=text.replace(new RegExp('nominal\\s+(?:tutarı|değeri)\\s+'+amountPattern(n)+'\\s+TL','giu'),(match,offset:number)=>
    /(?:tahvil|bono|borç|nakit|bütçe)[\p{L}\s]*$/iu.test(text.slice(0,offset))?match:'pay adedi '+n);
   text=text.replace(new RegExp(exact+'\\s+(?:TL\\s+)?(?:toplam\\s+)?nominal(?:\\s+tutarlı)?(?=\\s+(?:geri\\s+)?(?:alım|alış|satım|satış))','giu'),n+' adet pay');
   text=text.replace(new RegExp(exact+'\\s+TL\\s+nominal\\s+tutarla','giu'),n+' adet pay üzerinden');
   text=text.replace(new RegExp(exact+'\\s+(?:TL\\s+)?nominal\\s+tutarlıydı','giu'),n+' adet payı kapsadı');
   text=text.replace(new RegExp(exact+'\\s+(?:TL\\s+)?nominal\\s+tutarlı(?=\\s+işlem)','giu'),n+' adet paylık');
   text=text.replace(new RegExp('(?:toplam\\s+)?nominal\\s+tutarlı\\s+(alış|alım|satış|satım)\\s+işlemi\\s+'+amountPattern(n)+'\\s+TL','giu'),(_m,side:string,offset:number)=>
    (offset===0?side[0].toLocaleUpperCase('tr-TR')+side.slice(1):side)+' miktarı '+n+' adet pay');
  }
  return text.replace(/adet pay (?:alım|alış|alımı) yaptı/giu,'adet pay aldı').replace(/adet pay (?:satım|satış|satışı) yaptı/giu,'adet pay sattı')
   .replace(/adet pay (alım|alış) gerçekleştir/giu,'adet pay alımı gerçekleştir').replace(/adet pay (satım|satış) gerçekleştir/giu,'adet pay satışı gerçekleştir')
   .replace(/adet pay (alım|alış)(?=\s+(?:bildiril|yapıl|gerçekleş|açıklan))/giu,'adet pay alımı')
   .replace(/adet pay (satım|satış)(?=\s+(?:bildiril|yapıl|gerçekleş|açıklan))/giu,'adet pay satışı')
   .replace(/adet pay (alım|alış|satım|satış)(?=\s+işlem)/giu,'adet paylık $1');
 };
 const rows=(values?:CardRow[])=>!Array.isArray(values)?values:values.map(row=>{
  if(typeof row?.label!=='string'||typeof row.value!=='string')return row;
  // In a data card the quantity label and value can live in separate cells.
  const nominal=/nominal/iu.test(row.label+' '+row.value)&&!/(?:tahvil|bono|borç|nakit|bütçe|fiyat|bedel)/iu.test(row.label);
  const n=nominal?amounts.find(n=>new RegExp('^'+amountPattern(n)+'(?:\\s+TL)?(?:\\s+(?:toplam\\s+)?nominal(?:\\s+(?:tutar[ıi]?|değer[iı]?|değerli|tutarlı))?)?(?:\\s+pay)?$','iu').test(row.value.trim())):undefined;
  return {label:n?row.label.replace(/nominal\s+(?:tutar[ıi]?|değer[iı]?)/iu,'pay adedi').replace(/\s*\(TL\)/iu,''):row.label,value:n?n+' adet pay':replace(row.value)};
 });
 const claims=Array.isArray(draft.claims)?draft.claims.map(c=>{
  const text=replace(c.text);if(!Array.isArray(c.evidence))return {...c,text};
  const evidence=[...c.evidence];
  for(const p of proof)if(new RegExp('(?<![\\d.,])'+amountPattern(p.amount)+'(?![\\d.,])').test(text)&&c.evidence.some(e=>e.document===p.document&&e.passage+'_units'===p.passage)&&!evidence.some(e=>e.document===p.document&&e.passage===p.passage))evidence.push({document:p.document,passage:p.passage,quote:p.quote});
  return {...c,text,evidence};
 }):draft.claims;
 const card_data=draft.card_data&&typeof draft.card_data==='object'?{...draft.card_data,
  ...(draft.card_data.buy?{buy:rows(draft.card_data.buy)}:{}),...(draft.card_data.sell?{sell:rows(draft.card_data.sell)}:{}),...(draft.card_data.holdings?{holdings:rows(draft.card_data.holdings)}:{}),...(draft.card_data.metrics?{metrics:rows(draft.card_data.metrics)}:{})}:draft.card_data;
 return {...draft,headline:replace(draft.headline),body:replace(draft.body),card_headline:replace(draft.card_headline),card_body:replace(draft.card_body),...(card_data?{card_data}:{}),claims};
}
