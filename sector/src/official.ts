// Adapted from the committed Her An Borsa SPK parser; no old database/API used.
import {stripHtml} from './utils/text';
import {parseHTML} from 'linkedom';
export function parseSpk(html:string,base:string):{number:string;url:string;published_at:string}[] {
 const months:Record<string,string>={ocak:'01',şubat:'02',mart:'03',nisan:'04',mayıs:'05',haziran:'06',temmuz:'07',ağustos:'08',eylül:'09',ekim:'10',kasım:'11',aralık:'12'};
 const result=new Map<string,{number:string;url:string;published_at:string}>();
 const {document}=parseHTML(html);
 for(const link of document.querySelectorAll('a[href]')) {
  const href=link.getAttribute('href')??'';if(!/\.pdf(?:\?|$)/i.test(href))continue;
  const surrounding=stripHtml(link.textContent??'');
  const number=surrounding.match(/20\d{2}\s*\/\s*\d+/)?.[0].replace(/\s/g,'');
  const date=surrounding.match(/Yayımlanma\s*:\s*(\d{1,2})\s+([\p{L}]+)\s+(20\d{2})/iu);
  if(!number||!date)continue;const month=months[date[2].toLocaleLowerCase('tr-TR')];if(!month)continue;
  result.set(number,{number,url:new URL(href,base).href,published_at:new Date(`${date[3]}-${month}-${date[1].padStart(2,'0')}T00:00:00+03:00`).toISOString()});
 }
 return [...result.values()].sort((a,b)=>b.published_at.localeCompare(a.published_at));
}
