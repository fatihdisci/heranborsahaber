/* No third-party resources, fetches, analytics, storage or article HTML rendering. */
'use strict';
const $ = id => document.getElementById(id);
async function decodePayload(fragment) {
  if (!/^#v1\.[A-Za-z0-9_-]+$/.test(fragment) || fragment.length > 200000) throw Error('Geçersiz aktarım bağlantısı. Telegram’daki düğmeyi yeniden aç.');
  const raw = fragment.slice(4).replace(/-/g, '+').replace(/_/g, '/');
  const bytes = Uint8Array.from(atob(raw + '='.repeat((4-raw.length%4)%4)), c => c.charCodeAt(0));
  const reader = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')).getReader();
  const chunks=[]; let size=0;
  for (;;) {
    const {value,done}=await reader.read(); if(done)break;
    size+=value.length; if(size>500000){await reader.cancel();throw Error('Aktarım boyutu geçersiz.');}chunks.push(value);
  }
  const data=JSON.parse(await new Blob(chunks).text());
  if(data.v!==1 || typeof data.prompt!=='string' || typeof data.title!=='string' || [...data.prompt].length!==data.chars)throw Error('Aktarım eksik; Telegram’dan tekrar aç.');
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(data.prompt))),b=>b.toString(16).padStart(2,'0')).join('');
  if(hash!==data.sha256)throw Error('Aktarım doğrulanamadı; Telegram’dan tekrar aç.');
  return data;
}
async function copyPrompt() {
  const text=$('text');
  try {
    if(navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text.value);
    else throw Error('clipboard_unavailable');
  } catch (_) {
    // Older iOS WebViews require a focused selection during the same user gesture.
    text.closest('details').open=true;text.focus();text.select();text.setSelectionRange(0,text.value.length);
    if(!document.execCommand('copy')){$('status').textContent='Metnin tamamı seçildi. Kopyala’ya dokun.';return;}
  }
  $('status').textContent='Prompt ve haberin tamamı kopyalandı. GPT’de bir sohbete yapıştır.';
  $('copy').textContent='Tekrar kopyala';
}
async function start() {
  if(!location.hash)return;
  try {
    const data=await decodePayload(location.hash);
    $('title').textContent=data.title;$('count').textContent=data.chars.toLocaleString('tr-TR')+' karakter · eksiksiz aktarım';
    $('text').value=data.prompt;$('content').hidden=false;$('copy').disabled=false;
    $('description').textContent='Tamamını kopyala, GPT’ye yapıştır; yalnız tweet taslağı iste.';
    $('status').textContent='Kopyalamak için düğmeye dokun.';
    $('copy').onclick=copyPrompt;
    history.replaceState(null,'',location.pathname); // Do not leave article data in browser history.
  }catch(error){$('error').textContent=error.message || 'Aktarım açılamadı. Telegram’daki düğmeyi yeniden aç.';$('error').hidden=false;}
}
start();
window.addEventListener('hashchange', start);
