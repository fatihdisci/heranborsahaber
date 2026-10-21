import {readFile,writeFile,mkdir,unlink,open} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {homedir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {png} from './render_local';
import {draftCard} from '../src/card';
import {sha256} from '../src/utils/text';
import {acceptHermes} from '../src/ai';
import type {Draft,Document} from '../src/types';
import {scanOfficial} from './official_bridge';
type Config={url:string;token:string;hermesPython:string;hermesRoot:string;profile:string};
const root=fileURLToPath(new URL('../',import.meta.url));
const configPath=process.env.SECTOR_CONFIG??`${homedir()}/Library/Application Support/sector-haber/bridge.json`;
const config=JSON.parse(await readFile(configPath,'utf8')) as Config;
const base=new URL(config.url);if(base.protocol!=='https:'&&!['127.0.0.1','localhost'].includes(base.hostname))throw new Error('https_required');
async function api(path:string,payload:unknown):Promise<unknown> {
 const r=await fetch(new URL(path,base),{method:'POST',headers:{Authorization:'Bearer '+config.token,'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(40_000)});
 if(!r.ok)throw new Error(`bridge_http_${r.status}`);return r.json();
}
async function run():Promise<void> {
 if(Date.now()-lastOfficial>10*60_000){try{await scanOfficial(api,configPath+'.official-state');lastOfficial=Date.now();}catch{lastOfficial=Date.now()-8*60_000;}}
 const job=await api('/api/bridge/lease',{}) as Record<string,unknown>|null;if(!job)return;
 job.profile=config.profile;
 const output=await new Promise<string>((resolve,reject)=>{
  const child=spawn(config.hermesPython,[root+'scripts/hermes_job.py'],{cwd:root,env:{PATH:process.env.PATH??'',HOME:homedir(),HERMES_HOME:config.profile,PYTHONPATH:config.hermesRoot},stdio:['pipe','pipe','pipe']});
  let result='',bytes=0;const timer=setTimeout(()=>child.kill('SIGTERM'),500_000);
  child.stdout.on('data',chunk=>{bytes+=chunk.length;if(bytes>500_000)child.kill('SIGTERM');else result+=chunk.toString();});
  child.stderr.resume(); // Never expose credential-bearing diagnostics.
  child.on('error',reject);child.on('close',code=>{clearTimeout(timer);code===0?resolve(result):reject(new Error('hermes_job_failed'));});
  child.stdin.end(JSON.stringify(job));
 });
 const result=JSON.parse(output) as {draft:Draft;audit:unknown;runtime:unknown};
 const documents=job.documents as Document[];acceptHermes(result.draft,result.audit,documents);
 const date=new Date().toLocaleDateString('tr-TR',{timeZone:'Europe/Istanbul'}),svg=draftCard(result.draft,documents.map(d=>d.source_name),date,true);
 await api('/api/bridge/result',{id:job.id,lease_token:job.lease_token,input_hash:job.input_hash,...result,card_date:date,svg_hash:await sha256(svg),png_base64:Buffer.from(await png(svg)).toString('base64')});
}
const lockPath=configPath+'.lock';let lock;
try{lock=await open(lockPath,'wx',0o600);await lock.writeFile(String(process.pid));}
catch{try{const pid=Number(await readFile(lockPath,'utf8'));process.kill(pid,0);throw new Error('bridge_already_running');}catch(e){if((e as NodeJS.ErrnoException).code!=='ESRCH')throw e;await unlink(lockPath);lock=await open(lockPath,'wx',0o600);await lock.writeFile(String(process.pid));}}
let stopping=false;process.on('SIGTERM',()=>{stopping=true;});process.on('SIGINT',()=>{stopping=true;});
let lastOfficial=0;
try {do {try{await run();await writeFile(configPath+'.status',JSON.stringify({checked_at:new Date().toISOString(),ok:true}),{mode:0o600});}catch{await writeFile(configPath+'.status',JSON.stringify({checked_at:new Date().toISOString(),ok:false,error:'bridge_job_or_connection_failed'}),{mode:0o600});}if(process.argv.includes('--once')||stopping)break;await new Promise(r=>setTimeout(r,30_000));}while(!stopping);}
finally{await lock.close();await unlink(lockPath).catch(()=>{});}
