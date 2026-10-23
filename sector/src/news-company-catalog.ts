import catalog from './data/news-companies.json';
export const COMPANY_CATALOG_VERSION=catalog.version;
export const COMPANY_CATALOG_PROVENANCE={version:catalog.version,source_url:catalog.source_url,retrieved_at:catalog.retrieved_at,source_sha256:catalog.source_sha256,companies_sha256:catalog.companies_sha256};
export const catalogEntities=catalog.companies.flatMap(c=>[c.title,...c.aliases].map(name=>({name,code:c.code,verified:true,excluded_contexts:c.excluded_contexts})));
export function matchingCompanies<T extends {name:string;code:string;verified:boolean;excluded_contexts?:string[]}>(text:string,entities:T[],fold:(s:string)=>string){
 const padded=' '+text+' ';
 const ownMention=(name:string)=>{const needle=' '+fold(name)+' ';let at=padded.indexOf(needle);while(at>=0){const tail=padded.slice(at+needle.length);if(!/^(?:(?:nin|in|un|nun|nın) )?(?:ana sirketi|ana ortagi|istiraki|bagli ortakligi|markasi)\b/.test(tail))return true;at=padded.indexOf(needle,at+needle.length);}return false;};
 const candidates=entities.filter(e=>e.verified&&ownMention(e.name)&&!e.excluded_contexts?.some(s=>padded.includes(' '+fold(s)+' ')));
 // An alias shared by distinct legal entities is not a verified identity.
 return candidates.filter(e=>new Set(entities.filter(x=>fold(x.name)===fold(e.name)).map(x=>x.code)).size===1);
}
