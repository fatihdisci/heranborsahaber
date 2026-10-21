"""Full PDF evidence: every page, native text/tables and visual evidence for scans.
No Java deserialization. Official KAP byte-array transport is unwrapped by TS.
"""
import hashlib,json,pathlib,subprocess,sys
import pdfplumber,pypdfium2
from PIL import Image

def ocr_text(blocks):
    rows=[]
    for block in sorted(blocks,key=lambda b:b['y']):
        row=next((r for r in rows if abs(r[0]-block['y'])<max(.004,min(block['height']*.45,.012))),None)
        if row is None:row=[block['y'],[]];rows.append(row)
        row[1].append(block)
    lines=[]
    for _,cells in sorted(rows):
        line=''
        for cell in sorted(cells,key=lambda b:b['x']):
            start=max(len(line)+2 if line else 0,round(cell['x']*220))
            line=line.ljust(start)+cell['text']
        lines.append(line.rstrip())
    return '\n'.join(lines)

def read_pdf(path,root,ocr):
    data=path.read_bytes()
    if len(data)>20_000_000 or not data.startswith(b'%PDF-'):raise ValueError('invalid_pdf')
    folder=root/hashlib.sha256(data).hexdigest();folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    passages=[];images=[];pages=[]
    renderer=pypdfium2.PdfDocument(data)
    try:
      with pdfplumber.open(path) as pdf:
        if not 0<len(pdf.pages)<=200:raise ValueError('pdf_page_limit')
        for number,page in enumerate(pdf.pages,1):
            text=(page.extract_text(layout=True) or '').strip()
            tables=page.extract_tables()
            # Scans and substantial embedded images must also reach both model passes.
            visual=len(page.chars)<30 or any(float(i.get('width',0))*float(i.get('height',0))>page.width*page.height*.12 for i in page.images)
            mode='native'
            if visual:
                if len(images)>=20:raise ValueError('pdf_visual_page_limit')
                image=folder/f'page-{number}.png'
                rp=renderer[number-1]; bitmap=rp.render(scale=2)
                try:bitmap.to_pil().save(image)
                finally:bitmap.close();rp.close()
                image.chmod(0o600);images.append(str(image))
                if len(page.chars)<30:
                    mode='ocr_visual'
                    raw=subprocess.run([str(ocr),str(image)],capture_output=True,text=True,timeout=45,check=True)
                    blocks=json.loads(raw.stdout)
                    vertical=sum(len(b['text']) for b in blocks if b['height']>b['width']*2)
                    if vertical>sum(len(b['text']) for b in blocks)*.5:
                        with Image.open(image) as im:im.rotate(-90,expand=True).save(image)
                        raw=subprocess.run([str(ocr),str(image)],capture_output=True,text=True,timeout=45,check=True)
                        blocks=json.loads(raw.stdout)
                    if not blocks:raise ValueError('pdf_page_unreadable')
                    # Keep spatial coordinates: table cells must not lose column/row context.
                    text='OCR metni (sayfa görüntüsüyle doğrulanmalı):\n'+ocr_text(blocks)
            if len(text)<20:raise ValueError('pdf_page_unreadable')
            passages.append({'id':f'page{number}','text':text})
            for i,table in enumerate(tables,1):
                if table:passages.append({'id':f'page{number}_table{i}','text':json.dumps(table,ensure_ascii=False)})
            pages.append({'page':number,'mode':mode,'tables':len(tables),'characters':len(text)})
    finally:renderer.close()
    body='\n\n'.join(p['id']+'\n'+p['text'] for p in passages)
    if len(body)>600_000:raise ValueError('pdf_text_limit')
    return {'body':body,'passages':passages,'images':images,'coverage':{'pages':pages,'page_count':len(pages),'complete':True}}
if __name__=='__main__':
    try:
        result=read_pdf(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3]))
        print(json.dumps(result,ensure_ascii=False))
    except Exception as e:
        error=str(e) if isinstance(e,ValueError) and str(e).replace('_','').isalnum() else 'pdf_extraction_failed'
        print(json.dumps({'error':error}),file=sys.stderr);sys.exit(1)
