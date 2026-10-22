import type {Document} from './types';
const fold=(s:string)=>s.toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i');
export function marketSelection(text:string):'buy'|'sell'|'both'|undefined {
 const t=fold(text.trim().split('\n')[0]);
 if(/^(?:ikisini de|iki tarafi|her iki tarafi|hem alinan|hem alis)/.test(t))return 'both';
 if(!/^(?:sadece|yalniz(?:ca)?|alinanlar|satilanlar|\/(?:alinanlar|satilanlar))\b/.test(t))return;
 const buy=/alinan|alis|alim|aldig/.test(t),sell=/satilan|satis|satim|sattig/.test(t);
 return buy&&sell?'both':buy?'buy':sell?'sell':undefined;
}
export function selectMarketDocument(doc:Document,focus?:'buy'|'sell'|'both'):Document {
 if(!focus||!doc.market_data)return doc;
 if(doc.market_data.kind==='custody'&&focus!=='both')throw Error('manual_market_focus_unsupported');
 return {...doc,market_data:{...doc.market_data,focus}};
}
export function marketInput(text:string):Document['market_data']|undefined {
 const clean=text.replace(/[\p{Extended_Pictographic}\uFE0F]/gu,'').trim();
 const normalized=clean.toLocaleLowerCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ı/g,'i');
 const institution=clean.match(/^\s*([^\n]+?)\s+KURUM\s+ANAL[İI]Z[İI]\s*$/imu);
 if(institution&&/en cok (?:alinan|satilan) hisseler/u.test(normalized))return {kind:'institutional',broker:institution[1].trim()};
 if(/araci kurum islem ozeti/u.test(normalized)&&/net alis/u.test(normalized)&&/net satis/u.test(normalized))return {kind:'broker_flow'};
 const custody=clean.match(/^\s*([A-Z][A-Z0-9]{3,4})\s+Takas\b/u);
 if(custody&&/toplam takas lotu/u.test(normalized)&&/saklama kuruluslari/u.test(normalized))return {kind:'custody',ticker:custody[1]};
 return undefined;
}
export function withMarketText(doc:Document):Document {
 if(doc.market_data&&doc.passages.some(p=>p.id==='market_units'&&p.text===doc.body))return doc;
 const data=marketInput(doc.body);if(!data)return doc;
 // Mr/Mn are source shorthand for billion/million, not raw TL amounts.
 let text=doc.body.replace(/([-+]?\d+(?:[.,]\d+)*)\s*(Mr|Mn)\s*(₺|TL)(?=$|[^\p{L}])/giu,(_m,n:string,scale:string)=>`${data.kind==='institutional'?n.replace('.',','):n} ${scale.toLowerCase()==='mr'?'milyar':'milyon'} TL`);
 if(data.kind==='institutional'){
  text=text.replace(/([-+]?\d+)\.(\d{1,2})\s*%/g,'$1,$2%');
  let side:'buy'|'sell'|undefined;const rows:NonNullable<NonNullable<Document['market_data']>['rows']>=[];
  for(const line of text.split('\n')){
   const f=fold(line);if(/en cok alinan hisseler/.test(f))side='buy';else if(/en cok satilan hisseler/.test(f))side='sell';
   const match=line.match(/^\s*\d+\.\s+([A-Z][A-Z0-9]{3,4})\s*:\s*(\d+(?:,\d+)?\s+(?:milyon|milyar) TL)\s*$/);
   if(side&&match)rows.push({side,symbol:match[1],volume:match[2],rank:Number(line.match(/^\s*(\d+)\./)![1])});
   else if(side&&/^\s*\d+\.\s+[A-Z]/.test(line))throw Error('manual_market_row_incomplete');
  }
  if(!rows.length)throw Error('manual_market_row_incomplete');
  data.rows=rows;data.tickers=[...new Set(rows.map(r=>r.symbol))];
 }
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
 return {...doc,body:text,market_data:data,...(data.ticker?{equity_codes:[data.ticker]}:data.tickers?{equity_codes:data.tickers}:{}),passages:[...doc.passages,{id:'market_units',text}]};
}
