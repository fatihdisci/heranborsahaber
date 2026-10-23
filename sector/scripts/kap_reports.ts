import {generalBuyback} from '../src/general-buyback';
import {KapStore} from '../src/kap/store';
import {KapClient} from '../src/kap/client';
import {istanbulDay,purchases,report,type Purchase} from '../src/kap/reports';
import type {Disclosure,Indices} from '../src/kap/parser';
export class KapReports {
 constructor(private store:KapStore,private client=new KapClient()){
  store.db.exec(`CREATE TABLE IF NOT EXISTS report_buybacks(id INTEGER PRIMARY KEY REFERENCES disclosures(id),rows_json TEXT,error TEXT,attempts INTEGER NOT NULL DEFAULT 0,next_try INTEGER NOT NULL DEFAULT 0);`);
  if(!store.rows<{name:string}>("PRAGMA table_info(report_buybacks)").some(c=>c.name==='version'))store.db.exec("ALTER TABLE report_buybacks ADD COLUMN version INTEGER NOT NULL DEFAULT 0");
 }
 async cacheOne(at=Date.now()){
  const day=istanbulDay(at),start=day+'T00:00:00+03:00';
  const r=this.store.row<{id:number}>(`SELECT d.id FROM disclosures d LEFT JOIN report_buybacks b ON b.id=d.id WHERE julianday(d.published_at)>=julianday(?) AND julianday(d.published_at)<=julianday(?) AND json_extract(d.metadata,'$.title') LIKE '%Geri Alınmasına%' AND (b.id IS NULL OR (b.version<2 AND b.error IS NULL) OR (b.error IS NOT NULL AND b.attempts<3 AND b.next_try<=?)) ORDER BY d.id DESC LIMIT 1`,start,new Date(at).toISOString(),at);
  if(!r)return;
  let rows:Purchase[]|null=null,error:string|null=null;
  try{rows=purchases(await this.client.fullText(r.id));}catch(e){error=e instanceof Error&&/^[a-z_]+$/.test(e.message)?e.message:'kap_report_read_failed';}
  this.store.run(`INSERT INTO report_buybacks(id,rows_json,error,attempts,next_try,version) VALUES(?,?,?,1,?,2) ON CONFLICT(id) DO UPDATE SET rows_json=excluded.rows_json,error=excluded.error,attempts=report_buybacks.attempts+1,next_try=excluded.next_try,version=2`,r.id,rows?JSON.stringify(rows):null,error,at+60000);
 }
 async build(kind:'circuit'|'buyback'|'general_buyback',at:number,now=Date.now()){
  if(!['circuit','buyback','general_buyback'].includes(kind)||!Number.isSafeInteger(at)||at>now+60000)throw Error('kap_report_invalid');
  const rows=this.store.rows<{metadata:string;rows_json:string|null;error:string|null}>(`SELECT d.metadata,b.rows_json,b.error FROM disclosures d LEFT JOIN report_buybacks b ON b.id=d.id WHERE julianday(d.published_at)>=julianday(?) AND julianday(d.published_at)<=julianday(?) AND d.first_seen<=?`,istanbulDay(at)+'T00:00:00+03:00',new Date(at).toISOString(),at);
  const listing=this.store.get<{at:number}>('last_listing');
  const gaps=this.store.row<{n:number}>("SELECT COUNT(*) n FROM gaps WHERE first_seen>=?",Date.parse(istanbulDay(at)+'T00:00:00+03:00'))?.n??0;
  const delayed=!listing||at-listing.at>180000||gaps;
  const coverage=kind==='circuit'?(delayed?'Toplayıcıda gecikme veya eksik kayıt olabilir; rapor kayıtlı bildirimlerle sınırlıdır.':'Rapor, KAP sistemine ulaşan günlük bildirimlerle sınırlıdır.'):(delayed?'Toplayıcıda gecikme veya eksik kayıt olabilir; rapor kayıtlı bildirimlerle sınırlıdır.':'Rapor komut saatine kadar sisteme alınan KAP kayıtlarıyla sınırlıdır.');
  const entries=rows.map(r=>({disclosure:JSON.parse(r.metadata) as Disclosure,purchases:r.rows_json?JSON.parse(r.rows_json):undefined,error:r.error??undefined}));
  const indices=this.store.get<Indices>('indices');return kind==='general_buyback'?generalBuyback(kind,entries,indices,at,coverage):report(kind,entries,indices,at,coverage);
 }
}
