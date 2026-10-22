import {telegram} from './telegram';
import type {Env} from './types';

/** Telegram slash-menu entries for commands handled by the owner bot. */
export const TELEGRAM_COMMANDS = [
 {command:'start',description:'Botu kullanmaya başla'},
 {command:'help',description:'Yardım ve kullanım bilgisi'},
 {command:'devrekesici',description:'Günün devre kesici raporu'},
 {command:'gerialim',description:'Günün ilk 10 pay geri alımı'},
 {command:'genelgerialim',description:'Tüm pay geri alımlarını tablo yap'},
 {command:'kurum',description:'Kurum özeti veya kurum adıyla analiz'},
 {command:'akd',description:'Hisse aracı kurum dağılımı: /akd ASELS'},
 {command:'takas',description:'Hisse takas dağılımı: /takas THYAO'},
 {command:'sorgular',description:'Kurum, AKD ve takas komutlarını açıkla'},
] as const;

export async function registerTelegramCommands(env:Env,fetcher:typeof fetch=fetch):Promise<void>{
 const body=new URLSearchParams({commands:JSON.stringify(TELEGRAM_COMMANDS),scope:JSON.stringify({type:'all_private_chats'}),language_code:'tr'});
 await telegram(env,'setMyCommands',body,fetcher);
}
