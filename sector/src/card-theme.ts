import type {Env,Template} from './types';
export type CardTheme='navy'|'paper';
export function legacyTheme(template:Template):CardTheme{return template==='info'||template==='economic_data'||template==='market'?'paper':'navy';}
export async function savedTheme(env:Env,articleId:string):Promise<CardTheme|null>{
 const row=await env.DB.prepare('SELECT value FROM system_state WHERE key=?').bind('card_theme:'+articleId).first<{value:string}>();
 if(!row)return null;
 if(row.value!=='navy'&&row.value!=='paper')throw new Error('invalid_saved_card_theme');
 return row.value;
}
export async function chooseTheme(env:Env,articleId:string,existingTemplate?:Template):Promise<CardTheme>{
 const saved=await savedTheme(env,articleId);if(saved)return saved;
 // Draw once per article, independent of topic; retries and edits reuse it.
 const theme=existingTemplate?legacyTheme(existingTemplate):(crypto.getRandomValues(new Uint8Array(1))[0]&1?'paper':'navy');
 await env.DB.prepare('INSERT OR IGNORE INTO system_state(key,value) VALUES(?,?)').bind('card_theme:'+articleId,theme).run();
 return (await savedTheme(env,articleId))!;
}
