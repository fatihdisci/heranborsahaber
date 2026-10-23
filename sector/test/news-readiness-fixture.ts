// Synthetic, offline human-review fixtures. Never used by application code or live config.
import type {Env,Source} from '../src/types';
import {recordNewsCandidate,NEWS_RULE_VERSION,type NewsPreferences} from '../src/news-routing';
import {newsReadiness,NEWS_READINESS_VERSION,type NewsReadinessRecord} from '../src/news-readiness';
export async function reviewFixture(env:Env,p:NewsPreferences,at=Date.now()){
 env.TELEGRAM_USER_ID??='7';
 const source={id:'review-fixture',name:'Fixture',family:'fixture',official:false} as Source;
 for(let i=0;i<12;i++){
  const title=['TCMB politika faizi kararını açıkladı','TCMB politika faizi beklentisi açıklandı','Yapay zeka etkinlik tanıtımı başladı'][i%3]+' '+i;
  const c=await recordNewsCandidate(env,{url:'https://example.org/review/'+i,title,summary:'Sabit test verisi: kaynak açıklaması yeterli uzunlukta ve yalnız yerel test içindir.',published_at:new Date(at-60000).toISOString()},source,i%2===0,at,p);
  await env.DB.prepare('INSERT OR REPLACE INTO news_feedback VALUES(?,?,?,?)').bind(8000+i,c.id,'review:'+c.decision.route,at).run();
 }
 const report=await newsReadiness(env,p,NEWS_RULE_VERSION,at);
 const review=(hash:string)=>({hash,reviewer:env.TELEGRAM_USER_ID!,reviewed_at:at});
 const record:NewsReadinessRecord={version:NEWS_READINESS_VERSION,rule_version:NEWS_RULE_VERSION,entity_review:{...review(report.hashes.entities),sources:p.entities.map(e=>({code:e.code,url:'https://www.kap.org.tr/tr/sirket-bilgileri/ozet/test-fixture',checked_at:at}))},scope_review:review(report.hashes.scope),evaluation_review:{...review(report.hashes.sample),accepted:true}};
 await env.DB.prepare('INSERT INTO system_state VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value').bind('news_filter_readiness',JSON.stringify(record)).run();
 return record;
}
