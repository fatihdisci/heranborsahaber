import {EQUITY,normalize,type Disclosure,type Indices} from './parser';
export const TOPICS=['dividend','buyback','financial','capital','business','share_trade','circuit','other'] as const;
export type Topic=typeof TOPICS[number];
export interface Preferences {
 version:1; funds:'instant'|'digest'|'off'; fundDigestTime:string; priorityIndices:boolean;
 otherCompanies:'important'|'topics'|'off'; otherTopics:Topic[];
 watchlist:{ticker:string;mode:'all'|'important'|'topics';topics:Topic[]}[]; excludedTitles:string[];
}
export const DEFAULTS:Preferences={version:1,funds:'off',fundDigestTime:'19:00',priorityIndices:true,otherCompanies:'important',otherTopics:[],watchlist:[],excludedTitles:['İhraç Belgesi','Fon İhraç Sözleşmesi','Kredi Kullanımı']};
export function preferences(value:unknown):Preferences {
 const p=value as Preferences;const topics=(x:unknown)=>Array.isArray(x)&&x.every(t=>TOPICS.includes(t));
 if(!p||p.version!==1||!['instant','digest','off'].includes(p.funds)||!/^([01]\d|2[0-3]):[0-5]\d$/.test(p.fundDigestTime)||typeof p.priorityIndices!=='boolean'||!['important','topics','off'].includes(p.otherCompanies)||!topics(p.otherTopics)||!Array.isArray(p.watchlist)||!Array.isArray(p.excludedTitles)||p.excludedTitles.some(t=>typeof t!=='string'||!t.trim()||t.length>200))throw new Error('kap_preferences_invalid');
 if(p.watchlist.some(w=>!w||!EQUITY.test(w.ticker)||!['all','important','topics'].includes(w.mode)||!topics(w.topics))||new Set(p.watchlist.map(w=>w.ticker)).size!==p.watchlist.length)throw new Error('kap_watchlist_invalid');
 return structuredClone(p);
}
export function classify(d:Disclosure):Topic[] {
 const t=normalize(d.title),result:Topic[]=[];
 if(/TEMETTU|KAR PAYI/.test(t))result.push('dividend');
 if(/GERI ALIM|GERI ALIN|GERI SATIM|GERI SATIS|GERI SATIL/.test(t))result.push('buyback');
 if(/FINANSAL (RAPOR|TABLO|SONUC)|FAALIYET RAPOR/.test(t))result.push('financial');
 if(/SERMAYE ART|SERMAYE AZAL|BEDELLI|BEDELSIZ/.test(t))result.push('capital');
 if(/YENI IS ILISK|SOZLESME|IHALE|SIPARIS/.test(t))result.push('business');
 if(/PAY (ALIM|SATIM|ALIS|SATIS)/.test(t)&&!result.includes('buyback'))result.push('share_trade');
 if(normalize(d.title+' '+(d.summary??'')).includes('DEVRE KESICI'))result.push('circuit');
 return result.length?result:['other'];
}
export function muted(title:string):boolean {
 const t=normalize(title);
 return /IC\s*TUZUK|FON GIDER BILGILERI|ARACI KURUMA ODENEN KOMISYON VE VARLIK ALIM SATIM BILGILERI|FON TOPLAM GIDER ORANI|FON TOPLAM GIDERININ DAGILIMI/.test(t)
 ||(/FAIZSIZ/.test(t)&&/PAY DISI SERMAYE PIYASASI ARACI/.test(t))
 ||(/KURUMSAL YONETIM BILGI FORMU/.test(t)&&/GUNCELLEME/.test(t)&&/YONETIM KURULU\s*[-–]?\s*2/.test(t));
}
export function important(d:Disclosure):boolean {
 const t=normalize(d.title);
 return !(/PORTFOY DAGILIM RAPORU|BORSA DISI VAAD SOZLESMESI|BORSA DISI REPO|BORSA DISI TERS REPO|FON SUREKLI BILGILENDIRME|KREDI DERECELENDIR|YATIRIMCI BILGI FORMU|RISK OLCUM|DEGERLEME ESASLARI|SIRKET GENEL BILGI FORMU|HAK KULLANIM SUREC DURUM/.test(t)||(/FAIZ/.test(t)&&/PAY DISI SERMAYE PIYASASI ARACI/.test(t))||muted(d.title));
}
export function criticalFund(d:Disclosure):boolean {
 const text=normalize(d.title+' '+(d.company??'')+' '+(d.summary??''));
 return (d.isFund||/FON|PORTFOY|TEFAS/.test(text))&&/TEMERRUT|TASFIYE|ISLEMLERIN DURDURUL|KATILMA PAYI IADESI|ODEME/.test(text);
}
export interface Decision {store:boolean;action:'off'|'instant'|'digest'|'circuit';reason:string;topics:Topic[];important:boolean;critical:boolean;indexTier:30|100|null;}
export function decide(d:Disclosure,p:Preferences,indices:Indices|null):Decision {
 const topics=classify(d),significant=important(d),critical=criticalFund(d),shares=topics.includes('buyback')||topics.includes('share_trade');
 const tracked=p.watchlist.filter(w=>d.subjectCodes.includes(w.ticker));
 const explicit=tracked.some(w=>w.mode==='all'||w.mode==='topics'&&w.topics.some(t=>topics.includes(t)));
 const selected=p.otherCompanies==='topics'&&p.otherTopics.some(t=>topics.includes(t));
 const store=significant||explicit||selected||shares||topics.includes('circuit')||(d.isFund&&p.funds!=='off');
 const indexTier=indices&&d.subjectCodes.some(c=>indices.bist30.includes(c))?30:indices&&d.subjectCodes.some(c=>indices.bist100.includes(c))?100:null;
 const result=(action:Decision['action'],reason:string):Decision=>({store,action:store?action:'off',reason,topics,important:significant,critical,indexTier});
 if(d.isFund&&p.funds==='off')return result('off','funds_off');
 if(shares)return result('instant','share_transaction_override');
 if(muted(d.title))return result('off','mandatory_mute');
 if(p.excludedTitles.some(t=>normalize(d.title).includes(normalize(t))))return result('off','excluded_title');
 if(critical)return result('instant','critical_fund');
 if(d.isFund)return result(p.funds==='instant'?'instant':'digest','fund_preference');
 const instant=topics.includes('circuit')?'circuit':'instant';
 if(tracked.length)return result(tracked.some(w=>w.mode==='all'||w.mode==='important'&&significant||w.mode==='topics'&&w.topics.some(t=>topics.includes(t)))?instant:'off','watchlist');
 if(p.priorityIndices&&indexTier&&significant)return result(instant,'index_priority');
 if(p.otherCompanies==='important'&&significant||selected)return result(instant,'other_companies');
 return result('off','other_companies_off');
}
export function digestAt(now:number,time:string):number {
 const local=new Date(now+3*3600_000);const [h,m]=time.split(':').map(Number);
 let due=Date.UTC(local.getUTCFullYear(),local.getUTCMonth(),local.getUTCDate(),h-3,m);
 if(due<=now)due+=86400_000;return due;
}
