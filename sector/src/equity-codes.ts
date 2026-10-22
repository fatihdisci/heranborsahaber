import type {Document} from './types';
// Explicit metadata or a labelled source code, never an inferred acronym.
export function verifiedEquityCodes(documents:Document[]):string[]{
 const text=documents.map(d=>d.title+'\n'+d.body).join('\n');
 return [...new Set(documents.flatMap(d=>d.equity_codes??[]).concat(
  [...text.matchAll(/(?:BIST|hisse kodu|borsa kodu)\s*[:：]\s*([A-Z][A-Z0-9]{3,4})(?![A-Z0-9])/g)].map(m=>m[1])
 ).filter((c):c is string=>typeof c==='string').map(c=>c.trim().toUpperCase()).filter(c=>/^[A-Z][A-Z0-9]{3,4}$/.test(c)))];
}
