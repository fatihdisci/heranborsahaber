import {spawn} from 'node:child_process';
import {mkdir,writeFile} from 'node:fs/promises';
import {homedir} from 'node:os';
import {join} from 'node:path';
import {pdfRoot,type PdfEvidence} from './pdf_reader';
import type {Document} from '../src/types';
export type ImageEvidence=PdfEvidence&Pick<Document,'market_data'>;
export async function readImage(bytes:Uint8Array):Promise<ImageEvidence>{
 if(bytes.length>20_000_000)throw Error('image_size_limit');
 const png=[137,80,78,71,13,10,26,10].every((n,i)=>bytes[i]===n),jpeg=bytes[0]===255&&bytes[1]===216&&bytes[2]===255,webp=Buffer.from(bytes.slice(0,4)).toString()==='RIFF'&&Buffer.from(bytes.slice(8,12)).toString()==='WEBP';
 if(!png&&!jpeg&&!webp)throw Error('image_format_unsupported');
 await mkdir(pdfRoot,{recursive:true,mode:0o700});
 const hash=Buffer.from(await crypto.subtle.digest('SHA-256',bytes as BufferSource)).toString('hex'),path=join(pdfRoot,hash+'.image');
 await writeFile(path,bytes,{mode:0o600});
 return new Promise((resolve,reject)=>{
  const child=spawn(join(homedir(),'Library/Application Support/sector-haber/pdf-venv/bin/python'),['scripts/read_image.py',path,pdfRoot,join(homedir(),'Library/Application Support/sector-haber/bin/pdf-ocr')],{stdio:['ignore','pipe','pipe']});let output='',error='';
  const timer=setTimeout(()=>child.kill('SIGKILL'),60_000);
  child.stdout.on('data',b=>{output+=b.toString();if(output.length>1_000_000)child.kill('SIGKILL');});child.stderr.on('data',b=>{if(error.length<1000)error+=b.toString();});
  child.on('error',e=>{clearTimeout(timer);reject(e);});child.on('close',code=>{
   clearTimeout(timer);if(code!==0){let reason='image_extraction_failed';try{const e=JSON.parse(error);if(/^image_[a-z_]+$/.test(e.error))reason=e.error;}catch{}reject(Error(reason));return;}
   try{const d=JSON.parse(output) as ImageEvidence;if(!d.body||!d.passages?.length||!d.images?.length||!d.coverage?.complete)throw Error('image_incomplete');resolve(d);}catch(e){reject(e);}
  });
 });
}
