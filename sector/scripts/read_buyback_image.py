"""Read a ruled buyback table through the existing macOS Vision OCR binary.
Physical grid rows are the coverage contract. Blank pixels != unread text.
No KAP fetch, inferred prices, nominal-to-lot conversion or model provider.
"""
import json,pathlib,re,subprocess,sys,tempfile
from PIL import Image

HOMO=str.maketrans('АВЕКМНОРСТХУ','ABEKMHOPCTXY')
def groups(values):
    out=[]
    for v in values:
        if not out or v>out[-1][-1]+1:out.append([])
        out[-1].append(v)
    return [round(sum(g)/len(g)) for g in out]

def extract(path,blocks,retry=None):
    with Image.open(path) as source:
        w,h=source.size
        if w>12000 or h>12000 or w*h>25_000_000:raise ValueError('buyback_image_dimensions')
        im=source.convert('L')
    pix=im.load()
    ys=groups([y for y in range(h) if sum(pix[x,y]<100 for x in range(2,w-2))>w*.85])
    xs=groups([x for x in range(w) if sum(pix[x,y]<100 for y in range(h//8,h-2))>(h-h//8-2)*.85])
    if len(xs)!=6 or len(ys)<4:raise ValueError('buyback_grid_unreadable')
    text=' '.join(b['text'] for b in blocks).lower()
    if not all(s in text for s in ['nominal','ticker','transaction date','total']):raise ValueError('buyback_headers_unreadable')
    headers=[b for b in blocks if b['text'].strip().lower()=='ticker']
    if len(headers)!=1:raise ValueError('buyback_headers_unreadable')
    header_y=(headers[0]['y']+headers[0]['height'])*h
    start=next((y for y in ys if y>header_y),None)
    if start is None:raise ValueError('buyback_headers_unreadable')
    rows=[]
    for y0,y1 in zip(ys,ys[1:]):
        if y0<start:continue
        if y1-y0<12:raise ValueError('buyback_grid_unreadable')
        cells=[]
        for x0,x1 in zip(xs,xs[1:]):
            found=sorted([b for b in blocks if x0<=(b['x']+b['width']/2)*w<=x1 and y0<=(b['y']+b['height']/2)*h<=y1],key=lambda b:b['x'])
            value=' '.join(b['text'] for b in found).strip()
            if not value:
                ink=sum(pix[x,y]<160 for y in range(y0+5,y1-5) for x in range(x0+5,x1-5))
                if ink>8:raise ValueError('buyback_unread_cell')
            cells.append(value or None)
        if not cells[0] or not cells[1]:raise ValueError('buyback_missing_identity')
        original=list(cells)
        patterns=[r'[A-ZА-Яа-я][A-ZА-Яа-я0-9]{2,4}',r'\d{2}\.\d{2}\.\d{4}',r'(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?',r'(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?',r'(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?']
        for j,v in enumerate(cells):
            if v and not re.fullmatch(patterns[j],v):
                if not retry:raise ValueError('buyback_cell_syntax')
                cells[j]=retry(im.crop((xs[j]+5,y0+5,xs[j+1]-5,y1-5)))
                if not re.fullmatch(patterns[j],cells[j]):raise ValueError('buyback_cell_syntax')
        ticker=cells[0].upper().translate(HOMO)
        if not re.fullmatch('[A-Z][A-Z0-9]{2,4}',ticker):raise ValueError('buyback_ticker_unreadable')
        rows.append({'ticker':ticker,'day':cells[1],'nominal':cells[2],'price':cells[3],'amount':cells[4],'raw':cells,'ocr_original':original})
    if not rows or len(rows)>200:raise ValueError('buyback_row_capacity')
    return {'complete':True,'row_count':len(rows),'rows':rows,'reader':'vision-grid-v1','issues':[]}

def read(path,ocr):
    with Image.open(path) as im:
        if im.width*im.height>25_000_000 or max(im.size)>12000:raise ValueError('buyback_image_dimensions')
        im.verify()
    result=subprocess.run([str(ocr),str(path)],capture_output=True,text=True,timeout=60,check=True)
    def retry(crop):
        from PIL import ImageOps
        with tempfile.TemporaryDirectory(prefix='endeks-cell-') as tmp:
            target=pathlib.Path(tmp)/'cell.png'
            crop=crop.resize((crop.width*4,crop.height*4))
            crop.save(target)
            r=subprocess.run([str(ocr),str(target)],capture_output=True,text=True,timeout=15,check=True)
            return ' '.join(b['text'] for b in sorted(json.loads(r.stdout),key=lambda b:b['x']))
    return extract(path,json.loads(result.stdout),retry)
if __name__=='__main__':
    try:print(json.dumps(read(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2])),ensure_ascii=False))
    except Exception as e:
        code=str(e) if isinstance(e,ValueError) and re.fullmatch('buyback_[a-z_]+',str(e)) else 'buyback_reader_failed'
        print(json.dumps({'error':code}),file=sys.stderr);sys.exit(1)
