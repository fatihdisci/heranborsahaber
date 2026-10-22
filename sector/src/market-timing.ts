import type {Document} from './types';
export const MARKET_PERIODS=['Açılışın ilk dakikaları','Gün ortası','Kapanışa doğru','Gün sonu'] as const;
export function marketPeriod(sentAt:number):string|undefined {
 if(!Number.isSafeInteger(sentAt)||sentAt<=0||sentAt>253402300799)return;
 const hour=Number(new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Istanbul',hour:'2-digit',hourCycle:'h23'}).format(new Date(sentAt*1000)));
 return hour>=10&&hour<11?MARKET_PERIODS[0]:hour>=11&&hour<14?MARKET_PERIODS[1]:hour>=14&&hour<18?MARKET_PERIODS[2]:hour>=18&&hour<22?MARKET_PERIODS[3]:undefined;
}
export function withMarketTiming(doc:Document,sentAt?:number,sourceText?:string):Document {
 if(!doc.market_data||doc.market_data.submitted_at||sentAt===undefined||!marketPeriod(sentAt))return doc;
 const date=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Istanbul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(sentAt*1000));
 const text=sourceText??[doc.body,...doc.passages.filter(p=>p.id!=='market_submission_context').map(p=>p.text)].join('\n'),dates:string[]=[];
 const iso=(y:string,m:string,d:string)=>`${y}-${m.padStart(2,'0')}-${d.padStart(2,'0')}`;
 for(const m of text.matchAll(/\b(20\d{2})-(\d{2})-(\d{2})\b/g))dates.push(iso(m[1],m[2],m[3]));
 for(const m of text.matchAll(/\b(\d{1,2})[.\/-](\d{1,2})[.\/-](20\d{2})\b/g))dates.push(iso(m[3],m[2],m[1]));
 const months=['ocak','şubat','mart','nisan','mayıs','haziran','temmuz','ağustos','eylül','ekim','kasım','aralık'];
 for(const m of text.toLocaleLowerCase('tr-TR').matchAll(/\b(\d{1,2})\s+(ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)\s+(20\d{2})\b/g))dates.push(iso(m[3],String(months.indexOf(m[2])+1),m[1]));
 // A forwarded historical snapshot must not become today's market report.
 const label=dates.some(d=>d!==date)?undefined:marketPeriod(sentAt);
 return {...doc,market_data:{...doc.market_data,submitted_at:sentAt,...(label?{editorial_period:label}:{})},passages:[...doc.passages,{id:'market_submission_context',text:label?`Sahibin Telegram gönderim saatine göre istediği editoryal başlık: ${label}. Bu yalnız gönderim zamanının başlık sınıflandırmasıdır; kaynak verisinin ölçüm saati, işlem dönemi veya kesin seans kapanışı teyidi değildir. Kaynaktaki tarih ve işlem niteliği korunur.`:'Kaynakta gönderim gününden farklı bir tarih var. Gönderim saatine göre gün içi başlık eklenmez; kaynak tarihi korunur.'}]};
}
