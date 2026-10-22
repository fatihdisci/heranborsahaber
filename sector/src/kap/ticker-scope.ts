import type {Disclosure,Indices} from './parser';

// Recent IPOs and the user-identified fund-crisis cohort. Index membership is
// read independently from KAP /tr/Endeksler and is never copied into this list.
export const RECENT_IPO_TICKERS = [
 'NETGL','BKRGY','INTET','KPEKS','CITAS','VEYAS','TKNKA',
 'KARCL','QUICK','MASFN','ALBTN','METEN','SARAE','ISVEA',
] as const;
export const FUND_CRISIS_TICKERS = [
 'KTLEV','TRHOL','TEHOL','ODINE','GUNDG','OZATD','DSTKF','KARCL','ASTOR',
] as const;

const USER_FOCUS_TICKERS=new Set<string>([...RECENT_IPO_TICKERS,...FUND_CRISIS_TICKERS]);
export function isRecentIpoTicker(ticker:string):boolean{return (RECENT_IPO_TICKERS as readonly string[]).includes(ticker.toUpperCase());}

/** Return only source-identified codes included in the active editorial scope. */
export function focusedDisclosureTickers(d:Pick<Disclosure,'subjectCodes'|'relatedCodes'>,indices:Indices|null):string[]{
 const codes=d.subjectCodes.length?d.subjectCodes:d.relatedCodes;
 return [...new Set(codes.map(c=>c.toUpperCase()).filter(c=>USER_FOCUS_TICKERS.has(c)||!!indices&&(indices.bist30.includes(c)||indices.bist100.includes(c))))];
}
