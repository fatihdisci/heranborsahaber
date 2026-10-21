import type {Document,Draft} from './types';
const fold=(s:string)=>s.normalize('NFKC').toLocaleLowerCase('tr-TR').replace(/ı/g,'i');
export function editorialPolicy(documents:Document[]){
 const text=documents.map(d=>d.title+'\n'+d.body).join('\n');
 // Only explicit source codes: never infer a ticker from an uppercase acronym.
 const codes=[...new Set(documents.flatMap(d=>d.equity_codes??[]).concat(
  [...text.matchAll(/(?:BIST|hisse kodu|borsa kodu)\s*[:：]\s*([A-Z]{4,5})(?![A-Z])/g)].map(m=>m[1])
 ).filter(c=>/^[A-Z]{4,5}$/.test(c)))];
 const fund=/(?:^|[^\p{L}\p{N}])(?:fon(?:lar(?:i(?:n(?:in)?)?|da|dan|a|in)?|un|u|a|da|dan|daki|unun)?|tefas|pblk)(?=$|[^\p{L}\p{N}])/u.test(fold(text));
 const bist=codes.length>0||/\bbist\b|borsa istanbul/i.test(fold(text));
 return {required_hashtags:fund?['#Fon','#PBLK','#Tasfiye']:bist?['#Borsa','#BIST',...(codes.length===1?['#'+codes[0]]:[])]:[],verified_equity_codes:codes,
  publisher_names:[...new Set(documents.filter(d=>!d.official).map(d=>d.source_name))],
  instruction:'Yayıncıya göre/haberine göre veya Kaynak satırı yazma. Kaynak düğmede bulunur. İddia, koşul ve açıklamanın gerçek sahibini koru. Etiketler 2–3 adet; required_hashtags zorunludur. Fon içeriklerinde yalnız #Fon #PBLK #Tasfiye kullan; bu üç etiket hisse etiketlerinden önceliklidir. Diğer içeriklerde doğrulanmış tek şirket kodu varsa kullan. BIST dışındaki haberleri BIST diye etiketleme.'};
}
export function hasPublisherAttribution(text:string,names:string[]):boolean {
 const t=fold(text);
 if(/(?:^|\n)\s*kaynak\s*:/i.test(t)||/(?:haberine|haberlerinde|aktardiğina|aktardigina)\s+göre/i.test(t))return true;
 return names.filter(Boolean).some(name=>{
  const pattern=fold(name).replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/[-\s]+/g,'[-\\s]*');
  return new RegExp(pattern+"(?:['’]?[a-zçğıöşü]+)?\\s+(?:haberine|haberindeki|aktardiğina|aktardigina|bildirdiğine|bildirdigine|göre|kaynakli|tarafindan aktarilan)",'iu').test(t);
 });
}
export function styleIssues(draft:Draft,documents:Document[]):string[]{
 const p=editorialPolicy(documents),issues:string[]=[];
 if(invalidEmojiPlacement(draft))issues.push('invalid_emoji_placement');
 if(hasPublisherAttribution([draft.headline,draft.body,draft.card_headline,draft.card_body].join('\n'),p.publisher_names))issues.push('publisher_attribution');
 if(p.required_hashtags.some(tag=>!draft.hashtags.some(t=>fold(t)===fold(tag))))issues.push('missing_market_hashtags');
 return issues;
}

const emoji=/[\p{Extended_Pictographic}\p{Regional_Indicator}\u20e3]/u;
export function headlineWithEmoji(headline:string):string{headline=headline.replace(/^\s*🏢\uFE0F?\s*/u,'📢 ');return !headline.trim()||emoji.test(headline)?headline:'📢 '+headline.trim();}
export function invalidEmojiPlacement(draft:Draft):boolean {
 const headline=draft.headline.trim();
 const rest=headline.replace(/^(?:📢|🚨|📊|🏦|🌍|⚡|💻|📈|📉)\uFE0F?\s+/u,'');
 return emoji.test(rest)||[draft.body,draft.card_headline,draft.card_body,...draft.hashtags].some(t=>emoji.test(t??''));
}
