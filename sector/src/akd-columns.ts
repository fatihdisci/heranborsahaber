import type {CardRow} from './types';
// Decode only explicit legacy/model value formats. Never infer currency or unit.
export function akdColumns(row:CardRow):{ratio:string;quantity:string;unit:string;cost:string}|null {
 const number='[-+−]?\\d+(?:[.,]\\d+)*';
 const full=new RegExp(`^\\s*(%${number}|${number}%)\\s*[·|;]\\s*(${number})\\s*(lot|adet|pay)\\s*[·|;]\\s*(${number}(?:\\s*(?:TL|₺))?)\\s*$`,'iu').exec(row.value);
 if(full)return {ratio:full[1],quantity:full[2],unit:full[3].toLocaleLowerCase('tr-TR'),cost:full[4]};
 const amount=new RegExp(`^\\s*(${number})\\s*(lot|adet|pay)(?:\\s+net\\s+(?:satış|satım|alış|alım))?\\s*$`,'iu').exec(row.value);
 return amount?{ratio:'—',quantity:amount[1],unit:amount[2].toLocaleLowerCase('tr-TR'),cost:'—'}:null;
}
