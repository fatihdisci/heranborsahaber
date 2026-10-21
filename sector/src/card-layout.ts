import type {Env} from './types';
export const CARD_LAYOUTS=['editorial','frame','rail','masthead','center','brief'] as const;
export type CardLayout=typeof CARD_LAYOUTS[number];
export function isCardLayout(value:unknown):value is CardLayout{return CARD_LAYOUTS.includes(value as CardLayout);}
export function nextLayout(current?:CardLayout):CardLayout {
 const choices=CARD_LAYOUTS.filter(l=>l!==current);
 const limit=Math.floor(256/choices.length)*choices.length;let n:number;
 do{n=crypto.getRandomValues(new Uint8Array(1))[0];}while(n>=limit);
 return choices[n%choices.length];
}
export async function savedLayout(env:Env,id:string):Promise<CardLayout|null>{
 const row=await env.DB.prepare('SELECT value FROM system_state WHERE key=?').bind('card_layout:'+id).first<{value:string}>();
 if(!row)return null;if(!isCardLayout(row.value))throw Error('invalid_card_layout');return row.value;
}
export async function chooseLayout(env:Env,id:string):Promise<CardLayout>{
 const saved=await savedLayout(env,id);if(saved)return saved;
 await env.DB.prepare('INSERT OR IGNORE INTO system_state(key,value) VALUES(?,?)').bind('card_layout:'+id,nextLayout()).run();
 return (await savedLayout(env,id))!;
}
