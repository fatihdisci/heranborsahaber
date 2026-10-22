import type {CardData,CardRow,Document} from './types';
export function cardDataFields(data?:CardData):[string,string][] {
 if(!data)return [];
 const values:[string,string][]=[];
 for(const key of ['ticker','as_of'] as const)if(typeof data[key]==='string')values.push(['card_data.'+key,data[key]!]);
 for(const key of ['buy','sell','metrics'] as const)if(Array.isArray(data[key]))data[key]!.forEach((row,i)=>{if(typeof row?.label==='string')values.push([`card_data.${key}[${i}].label`,row.label]);if(typeof row?.value==='string')values.push([`card_data.${key}[${i}].value`,row.value]);});
 return values;
}
export function validateCardData(value:unknown,documents:Document[]):void {
 if(value===undefined)return;
 if(!value||typeof value!=='object'||Array.isArray(value))throw Error('invalid_card_data');
 const data=value as CardData;
 if(Object.keys(data).some(k=>!['ticker','as_of','buy','sell','metrics'].includes(k)))throw Error('invalid_card_data');
 for(const key of ['ticker','as_of'] as const)if(data[key]!==undefined&&(typeof data[key]!=='string'||!data[key]!.trim()||data[key]!.length>64))throw Error('invalid_card_data');
 for(const key of ['buy','sell','metrics'] as const){
  const rows=data[key];if(rows===undefined)continue;
  if(!Array.isArray(rows)||!rows.length||rows.length>(key==='metrics'?3:5)||rows.some((r:CardRow)=>!r||Object.keys(r).some(k=>!['label','value'].includes(k))||typeof r.label!=='string'||!r.label.trim()||r.label.length>60||typeof r.value!=='string'||!r.value.trim()||r.value.length>64))throw Error('invalid_card_data');
 }
 if(!cardDataFields(data).length)throw Error('invalid_card_data');
 const source=documents.map(d=>d.title+'\n'+d.body).join('\n');
 if(data.ticker&&(!/^[A-Z][A-Z0-9]{3,4}$/.test(data.ticker)||!documents.some(d=>d.equity_codes?.includes(data.ticker!))&&!new RegExp('(?<![A-Z0-9])'+data.ticker+'(?![A-Z0-9])').test(source)))throw Error('unsupported_card_ticker');
 // Audit evaluates row/value association and time period; this guard ensures
 // names themselves were supplied, rather than inferred from arbitrary codes.
 const norm=(s:string)=>s.normalize('NFKC').toLocaleLowerCase('tr-TR').replace(/\s+/g,' ');
 for(const row of [...data.buy??[],...data.sell??[]])if(!norm(source).includes(norm(row.label)))throw Error('unsupported_card_entity');
}
