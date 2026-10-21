import {sha256} from './utils/text';
import type {Draft,Document} from './types';
const normalized=(s:string)=>s.normalize('NFKC').toLocaleLowerCase('tr-TR').replace(/[^\p{L}\p{N}]+/gu,' ').trim();
export function titleSimilarity(a:string,b:string):number {
 const aa=new Set(normalized(a).split(' ').filter(x=>x.length>2));const bb=new Set(normalized(b).split(' ').filter(x=>x.length>2));
 if(!aa.size||!bb.size)return 0;const shared=[...aa].filter(x=>bb.has(x)).length;return shared/(aa.size+bb.size-shared);
}
export async function eventIdentity(draft:Draft,documents:Document[]):Promise<string> {
 // The model's event key cannot merge different named subjects or dates.
 const subjects=draft.entities.map(normalized).sort().join('|');
 const day=documents.map(d=>d.published_at?.slice(0,10)).find(Boolean)??'undated';
 return sha256([draft.category,subjects,normalized(draft.event_key),day].join('|'));
}
export function sameEvent(a:Draft,b:Draft):boolean {
 const subjects=a.entities.map(normalized),other=b.entities.map(normalized);
 if(!subjects.some(x=>other.includes(x)))return false;
 return normalized(a.event_key)===normalized(b.event_key)||titleSimilarity(a.headline,b.headline)>.72;
}
export function evidenceFamily(doc:Document):string {
 const text=doc.body.slice(0,5000);
 if(/(?:kaynak|source)\s*:\s*Reuters|\(Reuters\)/i.test(text))return 'wire-reuters';
 if(/(?:kaynak|source)\s*:\s*(?:AA|Anadolu)|\(AA\)/i.test(text))return 'wire-aa';
 if(/(?:kaynak|source)\s*:\s*Foreks/i.test(text))return 'wire-foreks';
 return doc.family;
}
