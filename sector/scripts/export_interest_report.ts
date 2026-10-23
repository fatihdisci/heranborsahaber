/** Read-only live-compatible export; never initializes a database or runs migrations. */
import {DatabaseSync} from 'node:sqlite';import {readFile,writeFile,mkdir} from 'node:fs/promises';import {join} from 'node:path';
import {interestReportData,formatInterestReport} from '../src/news-interest-report';import {evaluateNews,DEFAULT_NEWS_PREFERENCES,NEWS_RULE_VERSION} from '../src/news-routing';import {COMPANY_CATALOG_PROVENANCE} from '../src/news-company-catalog';import type {Source} from '../src/types';
const [dbPath,secretsPath,outDir]=process.argv.slice(2);if(!dbPath||!secretsPath||!outDir)throw Error('Usage: export_interest_report.ts database secrets-file output-directory');
const owner=String(JSON.parse(await readFile(secretsPath,'utf8')).TELEGRAM_USER_ID??'');if(!owner)throw Error('owner_missing');
const sql=new DatabaseSync(dbPath,{readOnly:true});sql.exec('PRAGMA query_only=ON; BEGIN');
try{
 if(sql.prepare('PRAGMA application_id').get()?.application_id!==0x53454354)throw Error('namespace_mismatch');
 const DB={prepare(text:string){const bind=(args:any[]=[])=>({bind:(...a:any[])=>bind(a),all:async()=>({results:sql.prepare(text).all(...args)}),first:async()=>sql.prepare(text).get(...args)??null});return bind();}} as unknown as D1Database;
 const data=await interestReportData({DB,TELEGRAM_USER_ID:owner});const at=Date.now();
 const comparisons=['ENDEKS HABER — AYRI DENEME DEĞERLENDİRMESİ',`Okuma zamanı: ${new Date(at).toISOString()}`,`Yeni kural: ${NEWS_RULE_VERSION}`,JSON.stringify(COMPANY_CATALOG_PROVENANCE),
 'Her aday kendi kayıtlı değerlendirme zamanında tekrar değerlendirildi; bugünün tarihiyle eski sayılmadı. Eski kararlar veya oylar yazılmadı. İnsan doğruluk etiketi yok; başarı oranı ölçülmedi. Beğeni rota onayı sayılmaz. KAP ve canlı ayarlar değişmedi.'];
 let compared=0,changed=0;
 for(const r of data.records){comparisons.push('',`${r.article_id} | ${r.title??'Eşleşmedi'} | seçim: ${r.choice??'kaldırılmış'}`,r.url??'Bağlantı yok');
  if(!r.current_decision||typeof r.summary!=='string'){comparisons.push('Deneme yapılamadı: aday veya özet saklama süresi dolmuş/eşleşmedi. Eksik geçmiş üretilmedi.');continue;}
  const d=evaluateNews({title:r.candidate_title,summary:r.summary,url:r.candidate_url,published_at:r.published_at},{id:r.source_id} as Source,DEFAULT_NEWS_PREFERENCES,r.evaluated_at);compared++;
  const before=r.current_decision;const different=JSON.stringify([before.route,before.reasons,before.confidence.codes,before.confidence.event,before.confidence.stage])!==JSON.stringify([d.route,d.reasons,d.confidence.codes,d.confidence.event,d.confidence.stage]);if(different)changed++;
  comparisons.push(`ESKİ (kayıtlı): ${JSON.stringify(before)}`,`YENİ (deneme): ${JSON.stringify({route:d.route,reasons:d.reasons,confidence:d.confidence,rule_version:NEWS_RULE_VERSION})}`,`Değişiklik: ${different?'var':'yok'}; teknik nedenler: ${[JSON.stringify(before.confidence.codes)!==JSON.stringify(d.confidence.codes)?'resmî şirket kataloğu':'',before.confidence.event!==d.confidence.event?'bağlamsal olay tespiti':'',before.confidence.stage!==d.confidence.stage?'beklenti/gerçekleşme/ihale aşaması ayrımı':'',JSON.stringify(before.reasons)!==JSON.stringify(d.reasons)?'piyasa ilgisi / tanıtım bağlamı gerekçesi':'',before.route!==d.route?'düzeltilmiş olay/ilgi bağlamına göre önerilen rota':''].filter(Boolean).join('; ')||'aynı karar veya gerekçe sınıflandırması'}`);
 }
 comparisons.push('',`Karşılaştırılan: ${compared}; karar/gerekçe/olay/şirket farkı: ${changed}. Bu sayılar doğruluk veya başarı oranı değildir.`);
 await mkdir(outDir,{recursive:true,mode:0o700});await writeFile(join(outDir,'geri-bildirim.txt'),formatInterestReport(data,at),{mode:0o600});await writeFile(join(outDir,'filtre-karsilastirma.txt'),comparisons.join('\n')+'\n',{mode:0o600});
 console.log(JSON.stringify({records:data.records.length,likes:data.records.filter(r=>r.choice==='like').length,dislikes:data.records.filter(r=>r.choice==='dislike').length,actions:data.actions.length,snapshots:data.snapshots.length,compared,changed,read_only:true}));
}finally{sql.exec('ROLLBACK');sql.close();}
