import {spawn} from 'node:child_process';
import {mkdir,writeFile,readdir,stat,rm} from 'node:fs/promises';
import {homedir} from 'node:os';
import {join,resolve,sep} from 'node:path';
import type {ChildProcess} from 'node:child_process';
export const pdfRoot=join(homedir(),'Library/Application Support/sector-haber/source-pdf');
export interface PdfEvidence {body:string;passages:{id:string;text:string}[];images:string[];coverage:{page_count:number;complete:boolean;pages:{page:number;mode:string;tables:number;characters:number}[]};}
export function killProcessTree(child:ChildProcess):void{
 if(!child.pid){try{child.kill('SIGKILL');}catch{/* process did not start */}return;}
 try{if(process.platform==='win32')child.kill('SIGKILL');else process.kill(-child.pid,'SIGKILL');}
 catch{try{child.kill('SIGKILL');}catch{/* already exited */}}
}
export function collectProcessOutput(child:ChildProcess,timeout:number,limit:number):Promise<{code:number|null;output:string;error:string}>{
 return new Promise((resolve,reject)=>{
  let output='',error='',settled=false;
  const finish=(fn:(value:any)=>void,value:any)=>{if(settled)return;settled=true;clearTimeout(timer);fn(value);};
  const timer=setTimeout(()=>{killProcessTree(child);finish(reject,new Error('pdf_timeout'));},timeout);
  child.stdout?.on('data',(b:Buffer)=>{output+=b.toString();if(output.length>limit){killProcessTree(child);finish(reject,new Error('pdf_output_limit'));}});
  child.stderr?.on('data',(b:Buffer)=>{if(error.length<1000)error+=b.toString().slice(0,1000-error.length);});
  child.on('error',e=>finish(reject,e));
  child.on('close',code=>finish(resolve,{code,output,error}));
 });
}
export async function cleanupPdfArtifacts(root=pdfRoot,now=Date.now(),ttl=24*3600_000,protectedPaths:Iterable<string>=[]):Promise<number>{
 let removed=0;const cutoff=now-ttl;
 const base=resolve(root),protectedSet=new Set([...protectedPaths].map(path=>resolve(path)).filter(path=>path===base||path.startsWith(base+sep)));
 async function visit(dir:string):Promise<void>{
  let entries;try{entries=await readdir(dir,{withFileTypes:true});}catch{return;}
  for(const entry of entries){const path=join(dir,entry.name);if(entry.isDirectory()){await visit(path);try{if((await readdir(path)).length===0)await rm(path,{recursive:true});}catch{/* concurrently removed */}continue;}
   try{const info=await stat(path);if(info.mtimeMs<cutoff&&!protectedSet.has(resolve(path))){await rm(path,{force:true});removed++;}}catch{/* concurrently removed */}
  }
 }
 await visit(root);return removed;
}
export async function readPdf(bytes:Uint8Array,timeout=180_000):Promise<PdfEvidence> {
 await mkdir(pdfRoot,{recursive:true,mode:0o700});
 const digest=Buffer.from(await crypto.subtle.digest('SHA-256',bytes as BufferSource)).toString('hex');
 const path=join(pdfRoot,digest+'.pdf');await writeFile(path,bytes,{mode:0o600});
 return new Promise((resolve,reject)=>{
  const child=spawn(join(homedir(),'Library/Application Support/sector-haber/pdf-venv/bin/python'),['scripts/read_pdf.py',path,pdfRoot,join(homedir(),'Library/Application Support/sector-haber/bin/pdf-ocr')],{stdio:['ignore','pipe','pipe'],detached:process.platform!=='win32'});
  collectProcessOutput(child,timeout,3_000_000).then(({code,output,error})=>{if(code!==0){let reason='pdf_extraction_failed';try{const e=JSON.parse(error);if(/^pdf_[a-z_]+$/.test(e.error))reason=e.error;}catch{}reject(new Error(reason));return;}
   try{const data=JSON.parse(output) as PdfEvidence;if(!data.coverage?.complete||data.coverage.pages.length!==data.coverage.page_count||!data.body||!data.passages.length)throw Error('pdf_incomplete');resolve(data);}catch(e){reject(e);}
  },reject);
 });
}
