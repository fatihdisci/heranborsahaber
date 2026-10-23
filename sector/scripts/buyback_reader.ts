import {spawn} from 'node:child_process';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {homedir,tmpdir} from 'node:os';
import {join} from 'node:path';
import {collectProcessOutput} from './pdf_reader';
// Temporary crops stay local and are removed even when OCR fails. The original
// source URL/hash and cell evidence remain in the existing editor document.
export async function readBuybackImage(bytes:Uint8Array):Promise<unknown>{
 if(bytes.length>3_000_000)throw Error('buyback_image_size_limit');
 const tmp=await mkdtemp(join(tmpdir(),'endeks-buyback-'));
 try{
  const path=join(tmp,'source.image');await writeFile(path,bytes,{mode:0o600});
  const root=join(homedir(),'Library/Application Support/sector-haber');
  const child=spawn(join(root,'pdf-venv/bin/python'),['scripts/read_buyback_image.py',path,join(root,'bin/pdf-ocr')],{stdio:['ignore','pipe','pipe'],detached:process.platform!=='win32'});
  const r=await collectProcessOutput(child,180000,1000000);
  if(r.code!==0){let error='buyback_reader_failed';try{const v=JSON.parse(r.error);if(/^buyback_[a-z_]+$/.test(v.error))error=v.error;}catch{}throw Error(error);}
  return JSON.parse(r.output);
 }finally{await rm(tmp,{recursive:true,force:true});}
}
