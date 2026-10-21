"""Extract every page; preserve table cell boundaries and page provenance."""
import io,json,sys,pdfplumber
data=sys.stdin.buffer.read(3_000_001)
if len(data)>3_000_000 or not data.startswith(b'%PDF-'):raise ValueError('invalid_pdf')
passages=[]
with pdfplumber.open(io.BytesIO(data)) as pdf:
    if len(pdf.pages)>40:raise ValueError('pdf_requires_manual_review')
    for number,page in enumerate(pdf.pages,1):
        text=page.extract_text(layout=True) or ''
        if len(text.strip())<20:raise ValueError('pdf_page_requires_ocr')
        passages.append({'id':f'page{number}','text':text.strip()})
        for i,table in enumerate(page.extract_tables(),1):
            if table:passages.append({'id':f'page{number}_table{i}','text':json.dumps(table,ensure_ascii=False)})
body='\n\n'.join(p['id']+'\n'+p['text'] for p in passages)
if len(body)>120_000:raise ValueError('pdf_requires_manual_review')
print(json.dumps({'body':body,'passages':passages},ensure_ascii=False))
