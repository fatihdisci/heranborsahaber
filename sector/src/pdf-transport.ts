// KAP sometimes wraps the PDF in Java's serialized byte[] transport. Match only
// the fixed byte-array header and exact length; never deserialize Java objects.
export function pdfBytes(raw:Uint8Array):Uint8Array {
 let b=raw;
 const header=Uint8Array.from([0xac,0xed,0,5,0x75,0x72,0,2,0x5b,0x42,0xac,0xf3,0x17,0xf8,6,8,0x54,0xe0,2,0,0,0x78,0x70]);
 if(raw.length>=27&&header.every((v,i)=>raw[i]===v)){
  const size=new DataView(raw.buffer,raw.byteOffset,raw.byteLength).getUint32(23);
  if(size!==raw.length-27)throw Error('pdf_transport_length');b=raw.slice(27);
 }
 if(b.length>20_000_000||String.fromCharCode(...b.slice(0,5))!=='%PDF-')throw Error('invalid_pdf');return b;
}
export async function boundedBytes(response:Response,max=20_000_027):Promise<Uint8Array> {
 const reader=response.body?.getReader();if(!reader)throw Error('empty_response');const parts:Uint8Array[]=[];let size=0;
 try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>max)throw Error('pdf_size_limit');parts.push(value);}}
 finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
 const out=new Uint8Array(size);let offset=0;for(const p of parts){out.set(p,offset);offset+=p.length;}return out;
}
