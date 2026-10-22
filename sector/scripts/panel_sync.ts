import {readFile,writeFile,rename,mkdir} from 'node:fs/promises';import {homedir} from 'node:os';import {resolve,sep} from 'node:path';
import {snapshot} from './panel_snapshot';import {validSnapshot} from '../src/miniapp/types';
const root=homedir()+'/Library/Application Support/sector-haber',dir=root+'/miniapp';
let stop=false;process.on('SIGTERM',()=>stop=true);process.on('SIGINT',()=>stop=true);
async function sync(){const config=JSON.parse(await readFile(dir+'/config.json','utf8'));const base=new URL(config.url);if(base.protocol!=='https:'||base.username||base.password||!base.hostname.endsWith('.workers.dev'))throw Error('panel_url_invalid');
 const state:Record<string,number>=JSON.parse(await readFile(dir+'/media-state.json','utf8').catch(()=>'{}'));
 const result=snapshot(root+'/sector-haber.sqlite',root+'/kap/kap.sqlite');if(!validSnapshot(result.snapshot))throw Error('panel_snapshot_invalid');
 const upload=async(path:string,body:Uint8Array|string,type:string)=>{const r=await fetch(new URL(path,base),{method:'PUT',headers:{authorization:'Bearer '+config.syncToken,'content-type':type},body:body as BodyInit,redirect:'error',signal:AbortSignal.timeout(20000)});await r.body?.cancel();if(!r.ok)throw Error('panel_upload_'+r.status);};
 let sent=0;for(const [id,key] of result.media){if(state[id]&&Date.now()-state[id]<10*86400000)continue;if(sent>=12||stop)break;const path=resolve(root+'/media',key);if(!path.startsWith(resolve(root+'/media')+sep))throw Error('panel_media_path');const bytes=await readFile(path).catch(()=>null);if(!bytes||bytes.length>5000000)continue;await upload('/sync/media/'+id,bytes,'image/png');state[id]=Date.now();sent++;}
 for(const item of result.snapshot.items)if(item.media&&!state[item.media])delete item.media;
 await upload('/sync/feed',JSON.stringify(result.snapshot),'application/json');for(const key of Object.keys(state))if(!result.media.has(key))delete state[key];
 await writeFile(dir+'/media-state.tmp',JSON.stringify(state),{mode:0o600});await rename(dir+'/media-state.tmp',dir+'/media-state.json');
 await writeFile(dir+'/health.json',JSON.stringify({ok:true,at:new Date().toISOString(),items:result.snapshot.items.length,images:sent}),{mode:0o600});
}
await mkdir(dir,{recursive:true,mode:0o700});
do{try{await sync();}catch(e){await writeFile(dir+'/health.json',JSON.stringify({ok:false,at:new Date().toISOString(),code:e instanceof Error&&/^panel_[a-z0-9_]+$/.test(e.message)?e.message:'panel_sync_failed'}),{mode:0o600});if(process.argv.includes('--once'))process.exitCode=1;}
 if(process.argv.includes('--once')||stop)break;for(let i=0;i<30&&!stop;i++)await new Promise(r=>setTimeout(r,1000));
}while(!stop);
