import type {Env} from './types';
import {publicationSQL} from './publication-assistant';
const parse=(value:string)=>{try{return JSON.parse(value);}catch{return {};}};
// Quoting alone does not stop spreadsheet formula execution.
const cell=(v:unknown)=>'"'+String(v??'').replace(/^[\s]*[=+@-]/,m=>"'"+m).replace(/"/g,'""')+'"';
export async function publicationCsv(env:Env,now=Date.now()) {
 const since=now-28*86400000;
 const rows=(await env.DB.prepare(`WITH publications AS (${publicationSQL}) SELECT p.*,
 LAG(p.published_at) OVER (ORDER BY p.published_at,p.draft_id) previous_at,
 COALESCE(snap.content,'{}') content,COALESCE(snap.source_urls,'[]') documents,snap.remote_url,
 (SELECT remote_id FROM x_posts x WHERE x.draft_id=p.draft_id AND x.state='sent' ORDER BY finished_at LIMIT 1) remote_id
 FROM publications p JOIN drafts d ON d.id=p.draft_id LEFT JOIN publication_snapshots snap ON snap.id=(SELECT ss.id FROM publication_snapshots ss WHERE ss.draft_id=p.draft_id AND ss.method=p.method AND ss.published_at=p.published_at LIMIT 1) WHERE p.published_at<=? ORDER BY p.published_at,p.draft_id`).bind(now).all<{draft_id:string;published_at:number;previous_at:number|null;method:string;content:string;documents:string;remote_id:string|null;remote_url:string|null}>()).results;
 const header=['kayit_id','yayin_zamani_istanbul','yontem','x_url','onceki_yayina_dakika','yayin_anindaki_baslik','yayin_anindaki_kategori','yayin_anindaki_sablon','dogrulanmis_hisse_sayisi','hisse_kodlari','kaynak_url','acil_rutin_manuel','deney_grubu_manuel','gosterim_15dk','gosterim_1s','gosterim_3s','gosterim_24s','gosterim_48s','begeni_24s','yeniden_paylasim_24s','yanit_24s','yer_imi_24s','profil_ziyareti_24s'];
 const lines=[header,...rows.filter(r=>r.published_at>=since).map(r=>{
  const d=parse(r.content),docs=parse(r.documents),list=Array.isArray(docs)?docs:[];
  const codes=[...new Set<string>(list.flatMap(x=>Array.isArray(x.equity_codes)?x.equity_codes:[]))].filter(c=>/^[A-Z][A-Z0-9]{3,4}$/.test(c));
  return [r.draft_id,new Date(r.published_at+10800000).toISOString().slice(0,19)+'+03:00',r.method,r.remote_id&&/^\d+$/.test(r.remote_id)?'https://x.com/endeks_haber/status/'+r.remote_id:r.remote_url??'',r.previous_at===null?'':((r.published_at-r.previous_at)/60000).toFixed(2),d.headline??'',d.category??'',d.template??'',codes.length,codes.join(' '),list[0]?.url??'',...Array(12).fill('')];
 })];
 return '\uFEFF'+lines.map(row=>row.map(cell).join(';')).join('\r\n');
}
