import type {Document} from './types';
export function marketInput(text:string):Document['market_data']|undefined {
 const clean=text.replace(/[\p{Extended_Pictographic}\uFE0F]/gu,'').trim();
 const normalized=clean.toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i');
 if(/araci kurum islem ozeti/u.test(normalized)&&/net alis/u.test(normalized)&&/net satis/u.test(normalized))return {kind:'broker_flow'};
 const custody=clean.match(/^\s*([A-Z][A-Z0-9]{3,4})\s+Takas\b/u);
 if(custody&&/toplam takas lotu/u.test(normalized)&&/saklama kuruluslari/u.test(normalized))return {kind:'custody',ticker:custody[1]};
 return undefined;
}
export function withMarketText(doc:Document):Document {
 if(doc.market_data&&doc.passages.some(p=>p.id==='market_units'&&p.text===doc.body))return doc;
 const data=marketInput(doc.body);if(!data)return doc;
 // Mr/Mn are source shorthand for billion/million, not raw TL amounts.
 let text=doc.body.replace(/([-+]?\d+(?:[.,]\d+)*)\s*(Mr|Mn)\s*(₺|TL)(?=$|[^\p{L}])/giu,(_m,n:string,scale:string)=>`${n} ${scale.toLowerCase()==='mr'?'milyar':'milyon'} TL`);
 if(data.kind==='broker_flow'){
  const sales=[...text.matchAll(/^\s*\d+\.\s+([^\n→]+)\s*→\s*-(\d+(?:[.,]\d+)*\s+(?:milyar|milyon) TL)/gmu)].map(m=>m[1].trim()+': net satım miktarı '+m[2]);
  if(sales.length)text+='\n\nNegatif net değerin satım miktarı karşılığı:\n'+sales.join('\n');
 }
 if(data.kind==='custody'){
  // A bare "108,10 Milyon %14,62" must not become "108,10 million
  // percent". Keep the lot quantity and ownership percentage in separate cells.
  text=text.replace(/^\s*(?:\d+\.\s+|📎\s*)?([^\n|]+?)\s+(\d+(?:[.,]\d+)*)\s+(Milyon|Milyar|Bin|Lot)\s*%(\d+(?:[.,]\d+)*)\s*$/gimu,(_m,label:string,n:string,scale:string,ratio:string)=>
   `${label.trim()} | Saklanan miktar: ${n} ${scale.toLocaleLowerCase('tr-TR')==='lot'?'lot':scale.toLocaleLowerCase('tr-TR')+' lot'} | Sermaye payı: %${ratio}`);
 }
 return {...doc,body:text,market_data:data,...(data.ticker?{equity_codes:[data.ticker]}:{}),passages:[...doc.passages,{id:'market_units',text}]};
}
