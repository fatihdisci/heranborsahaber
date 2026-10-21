import {spawn} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';
import {homedir} from 'node:os';
import registry from '../sources.json';
import {readPublic} from '../src/network';
import {parseSpk} from '../src/official';
import type {Document,Source} from '../src/types';
export async function scanOfficial(api:(path:string,value:unknown)=>Promise<unknown>,statePath:string):Promise<void> {
 const source=(registry as Source[]).find(s=>s.id==='spk')!;
 const feed=await readPublic(source.url,source.allowed_hosts,{Accept:'text/html,application/xhtml+xml'});
 const recent=parseSpk(feed.text,feed.url).filter(b=>Date.now()-Date.parse(b.published_at)<48*3600_000).slice(0,2);
 let seen:string[]=[];try{seen=JSON.parse(await readFile(statePath,'utf8'));}catch{}
 for(const item of recent){
  if(seen.includes(item.url))continue;
  const pdf=await readPublic(item.url,source.allowed_hosts,{Accept:'application/pdf'},fetch,true);
  const bytes=pdf.bytes!;const digest=Buffer.from(await crypto.subtle.digest('SHA-256',bytes as BufferSource)).toString('hex');
  const text=await new Promise<{body:string;passages:{id:string;text:string}[]}>((resolve,reject)=>{
   const child=spawn(`${homedir()}/Library/Application Support/sector-haber/pdf-venv/bin/python`,['scripts/pdf_text.py'],{stdio:['pipe','pipe','pipe']});let output='';
   const timer=setTimeout(()=>child.kill('SIGTERM'),45_000);child.stdout.on('data',b=>{output+=b.toString();if(output.length>400_000)child.kill('SIGTERM');});child.stderr.resume();
   child.on('error',reject);child.on('close',code=>{clearTimeout(timer);if(code!==0)reject(new Error('official_pdf_unreadable'));else try{resolve(JSON.parse(output));}catch(e){reject(e);}});child.stdin.end(bytes);
  });
  const document:Document={source_id:'spk',source_name:'SPK',family:'spk',official:true,url:item.url,title:`SPK Bülteni ${item.number}`,published_at:item.published_at,...text};
  await api('/api/bridge/official',{document,pdf_hash:digest});seen.push(item.url);
  await writeFile(statePath,JSON.stringify(seen.slice(-30)),{mode:0o600});
 }
}
