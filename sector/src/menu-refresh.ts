import type {Env} from './types';import {refreshDraftMenu} from './card-menu';import {refreshNewsMenu} from './news-menu';
export type MenuItem={kind:'draft'|'news';id:string;message_id:number;revision:number};
export async function menuPlan(env:Env):Promise<MenuItem[]>{
 const drafts=(await env.DB.prepare("SELECT id,message_id,revision,created_at FROM drafts WHERE message_id IS NOT NULL AND delivery_state IN ('sent','expired') ORDER BY created_at DESC,revision DESC").all<any>()).results;
 const news=(await env.DB.prepare("SELECT id,message_id FROM news_cards WHERE message_id IS NOT NULL AND state IN ('sent','failed','requested','model_queued','complete') ORDER BY created_at DESC").all<any>()).results;
 const seen=new Set<number>(),plan:MenuItem[]=[];
 for(const row of [...drafts.map(r=>({...r,kind:'draft' as const})),...news.map(r=>({...r,revision:0,kind:'news' as const}))])if(!seen.has(row.message_id)){seen.add(row.message_id);plan.push(row);}
 return plan;
}
export async function refreshMenuItem(env:Env,item:MenuItem):Promise<boolean>{
 // A stale plan must never attach old revision controls to a replacement message.
 const row=await env.DB.prepare(item.kind==='draft'?"SELECT id FROM drafts WHERE id=? AND message_id=? AND revision=? AND delivery_state IN ('sent','expired')":"SELECT id FROM news_cards WHERE id=? AND message_id=? AND ?=0 AND state IN ('sent','failed','requested','model_queued','complete')").bind(item.id,item.message_id,item.revision).first();
 if(!row)return false;
 return item.kind==='draft'?refreshDraftMenu(env,item.id):refreshNewsMenu(env,item.id,item.message_id);
}
