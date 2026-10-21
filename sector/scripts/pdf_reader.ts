import {spawn} from 'node:child_process';
import {mkdir,writeFile} from 'node:fs/promises';
import {homedir} from 'node:os';
import {join} from 'node:path';
export const pdfRoot=join(homedir(),'Library/Application Support/sector-haber/source-pdf');
export interface PdfEvidence {body:string;passages:{id:string;text:string}[];images:string[];coverage:{page_count:number;complete:boolean;pages:{page:number;mode:string;tables:number;characters:number}[]};}
export async function readPdf(bytes:Uint8Array,timeout=180_000):Promise<PdfEvidence> {
 await mkdir(pdfRoot,{recursive:true,mode:0o700});
 const digest=Buffer.from(await crypto.subtle.digest('SHA-256',bytes as BufferSource)).toString('hex');
 const path=join(pdfRoot,digest+'.pdf');await writeFile(path,bytes,{mode:0o600});
 return new Promise((resolve,reject)=>{
  const child=spawn(join(homedir(),'Library/Application Support/sector-haber/pdf-venv/bin/python'),['scripts/read_pdf.py',path,pdfRoot,join(homedir(),'Library/Application Support/sector-haber/bin/pdf-ocr')],{stdio:['ignore','pipe','pipe']});let output='',error='';
  const timer=setTimeout(()=>child.kill('SIGKILL'),timeout);child.stdout.on('data',b=>{output+=b.toString();if(output.length>3_000_000)child.kill('SIGKILL');});child.stderr.on('data',b=>{if(error.length<1000)error+=b.toString();});
  child.on('error',e=>{clearTimeout(timer);reject(e);});child.on('close',code=>{clearTimeout(timer);if(code!==0){let reason='pdf_extraction_failed';try{const e=JSON.parse(error);if(/^pdf_[a-z_]+$/.test(e.error))reason=e.error;}catch{}reject(new Error(reason));return;}
   try{const data=JSON.parse(output) as PdfEvidence;if(!data.coverage?.complete||data.coverage.pages.length!==data.coverage.page_count||!data.body||!data.passages.length)throw Error('pdf_incomplete');resolve(data);}catch(e){reject(e);}
  });
 });
}
