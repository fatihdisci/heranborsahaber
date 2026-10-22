import type {CardRow} from './types';
// Decode only explicit legacy/model value formats. Never infer currency or unit.
export function akdColumns(row:CardRow):{ratio:string|null;quantity:string|null;unit:string|null;cost:string|null}|null {
 const number='[-+−]?\\d+(?:[.,]\\d+)*';
 const parts=row.value.split(/[·|;]/).map(v=>v.trim());
 if(parts.length>=2&&parts.length<=3){
  const ratio=parts[0].match(new RegExp(`^(%${number}|${number}%)$`,'iu'))?.[1]??null;
  const q=parts.find(v=>new RegExp(`^${number}\\s*(?:lot|adet|pay)$`,'iu').test(v));
  const quantity=q?.match(new RegExp(`^(${number})\\s*(lot|adet|pay)$`,'iu'));
  const cost=parts.find(v=>new RegExp(`^${number}(?:\\s*(?:TL|₺))?$`,'iu').test(v)&&v!==q&&v!==parts[0])??null;
  if(ratio||quantity||cost)return {ratio,quantity:quantity?.[1]??null,unit:quantity?.[2].toLocaleLowerCase('tr-TR')??null,cost};
 }
 const amount=new RegExp(`^\\s*(${number})\\s*(lot|adet|pay)(?:\\s+net\\s+(?:satış|satım|alış|alım))?\\s*$`,'iu').exec(row.value);
 return amount?{ratio:null,quantity:amount[1],unit:amount[2].toLocaleLowerCase('tr-TR'),cost:null}:null;
}
