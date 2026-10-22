"""Read owner-forwarded images without treating OCR or a bot as an official feed."""
import hashlib,json,pathlib,re,subprocess,sys
from decimal import Decimal
from PIL import Image,ImageOps,ImageChops,ImageStat
from read_pdf import ocr_text

def rows(blocks):
    out=[]
    for b in sorted(blocks,key=lambda b:b['y']):
        row=next((r for r in out if abs(r[0]-b['y'])<.012),None)
        if row is None:row=[b['y'],[]];out.append(row)
        row[1].append(b)
    return [(y,sorted(cells,key=lambda b:b['x'])) for y,cells in sorted(out)]

def decimal_value(raw,percent=False):
    raw=raw.strip().replace('%','').replace('−','-')
    if not re.fullmatch(r'[-+]?\d+(?:[.,]\d{1,2})?',raw):raise ValueError('image_market_number_ambiguous')
    value=raw.replace('.',',')
    if percent and not 0<=Decimal(value.replace(',','.'))<=100:raise ValueError('image_market_number_ambiguous')
    return ('%' if percent else '')+value

def lot_value(raw):
    raw=raw.strip().replace('−','-')
    if not re.fullmatch(r'[-+]?(?:\d{1,3}(?:\.\d{3})+|\d+)',raw):raise ValueError('image_market_number_ambiguous')
    return raw+' lot'

def recover_labels(blocks,image,ocr):
    """Retry unread short cells using their real header pixels as OCR context.

    This adds no dictionary guesses. The original whole image remains the
    evidence shown to both model passes, and an unread cell still fails closed.
    """
    current=None;recovered=[];attempts=0
    for y,cells in rows(blocks):
        h={c['text'].upper().replace('İ','I'):c for c in cells}
        if all(k in h for k in ['KURUM','ORAN','NET LOT','MALIYET']):current=h;continue
        if not current:continue
        x=[current[k]['x'] for k in ['KURUM','ORAN','NET LOT','MALIYET']]
        if x!=sorted(x):raise ValueError('image_market_table_incomplete')
        cuts=[(x[i]+x[i+1])/2 for i in range(3)]
        cols=[[] for _ in range(4)]
        for c in cells:cols[sum(c['x']>=v for v in cuts)].append(c)
        if cols[0] or not all(cols[1:]):continue
        if attempts>=5:raise ValueError('image_market_table_incomplete')
        attempts+=1
        with Image.open(image) as original:
            w,hi=original.size;header=current['KURUM'];parts=[]
            for top,bottom in [(header['y']-.002,header['y']+header['height']+.006),(y-.005,y+max(c['height'] for c in cells)+.012)]:
                part=original.crop((int(w*max(0,x[0]-.003)),int(hi*max(0,top)),int(w*(cuts[0]-.005)),int(hi*min(1,bottom)))).convert('RGB')
                gray=ImageOps.grayscale(part);bg=int(ImageStat.Stat(gray).median[0]);mask=ImageChops.difference(gray,Image.new('L',gray.size,bg)).point(lambda v:255 if v>60 else 0)
                box=mask.getbbox()
                if not box:break
                part=part.crop(box);parts.append(part.resize((max(1,round(part.width*80/part.height)),80)))
            if len(parts)!=2:continue
            strip=Image.new('RGB',(sum(p.width for p in parts)+32,100),original.getpixel((0,0))[:3]);left=8
            for part in parts:strip.paste(part,(left,10));left+=part.width+8
            path=image.parent/f'label-{len(recovered)}.png';strip.save(path);path.chmod(0o600)
        retry=subprocess.run([str(ocr),str(path)],capture_output=True,text=True,timeout=10,check=True)
        result=json.loads(retry.stdout);text=' '.join(b['text'] for b in result).strip()
        if text.upper().startswith('KURUM'):
            name=text[5:].strip()
            if re.fullmatch(r'[^\W\d_][\w .&’\'-]{0,59}',name):recovered.append({'text':name,'x':x[0],'y':y,'width':cuts[0]-x[0],'height':max(c['height'] for c in cells),'confidence':min(b['confidence'] for b in result)})
    return blocks+recovered

def market_passages(blocks):
    grid=rows(blocks);tables=[]
    for i,(y,cells) in enumerate(grid):
        headers={re.sub(r'\s+',' ',c['text'].upper()).replace('İ','I'):c['x'] for c in cells}
        if all(h in headers for h in ['KURUM','ORAN','NET LOT','MALIYET']):tables.append((i,headers))
    if not tables:return None
    if len(tables)!=2:raise ValueError('image_market_table_incomplete')
    tickers={b['text'].strip() for b in blocks if b['y']<grid[tables[0][0]][0] and re.fullmatch(r'[A-Z][A-Z0-9]{3,4}',b['text'].strip())}
    if len(tickers)!=1:raise ValueError('image_market_ticker_ambiguous')
    ticker=tickers.pop();passages=[];sides=set()
    for n,(start,h) in enumerate(tables):
        columns=[h[k] for k in ['KURUM','ORAN','NET LOT','MALIYET']]
        if columns!=sorted(columns):raise ValueError('image_market_table_incomplete')
        boundaries=[(columns[j]+columns[j+1])/2 for j in range(3)]
        end=tables[n+1][0] if n+1<len(tables) else len(grid)
        parsed=[]
        for _,cells in grid[start+1:end]:
            parts=[[],[],[],[]]
            for c in cells:
                col=sum(c['x']>=x for x in boundaries);parts[col].append(c['text'])
            if not all(parts):
                if sum(bool(p) for p in parts[1:])>=2:raise ValueError('image_market_table_incomplete')
                continue
            name,ratio,lot,cost=[' '.join(p).strip() for p in parts]
            if len(name)>60:raise ValueError('image_market_table_incomplete')
            ratio=decimal_value(ratio,True);lot=lot_value(lot);cost=decimal_value(cost)
            side='satım' if lot.startswith('-') else 'alım'
            absolute=' | Net satım miktarı: '+lot[1:] if side=='satım' else ''
            parsed.append((side,f'Hisse kodu: {ticker} | Net {side} yapan kurum: {name} | Oran: {ratio} | Net lot: {lot}{absolute} | Maliyet: {cost} (para birimi görselde belirtilmemiş)'))
        if not 1<=len(parsed)<=20 or len({side for side,_ in parsed})!=1:raise ValueError('image_market_table_incomplete')
        sides.add(parsed[0][0])
        for j,(_,text) in enumerate(parsed):passages.append({'id':f'image_table{n+1}row{j+1}','text':text})
    if sides!={'alım','satım'}:raise ValueError('image_market_table_incomplete')
    dates=set(re.findall(r'\b(?:\d{4}-\d{2}-\d{2}|\d{2}\.\d{2}\.\d{4}|\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+20\d{2})\b',ocr_text(blocks),re.I))
    period='Görselde geçen tarih ifadeleri: '+', '.join(sorted(dates))+'. Veri dönemi yalnız ilgili başlıkla açıkça ilişkilendirilebiliyorsa kullanılır.' if dates else 'Kaynak görselde veri tarihi ve saati belirtilmemiş; bu nedenle güncel tarih veya anlık piyasa iddiası eklenemez.'
    metadata={'id':'image_metadata','text':f'Hisse kodu: {ticker}. Aracı kurum dağılımı. {period} Oran ve maliyet sütunundaki ondalık noktalar Türkçe virgüle dönüştürüldü; net lot sütunundaki binlik noktalar korundu. Maliyet için para birimi tahmin edilmez.'}
    return {'kind':'akd','ticker':ticker},[metadata,*passages]

def read_image(path,root,ocr):
    data=path.read_bytes()
    if len(data)>20_000_000:raise ValueError('image_size_limit')
    with Image.open(path) as probe:
        if probe.format not in ('PNG','JPEG','WEBP'):raise ValueError('image_format_unsupported')
        if not 100<=probe.width<=12000 or not 100<=probe.height<=12000 or probe.width*probe.height>25_000_000:raise ValueError('image_dimension_limit')
        probe.verify()
    folder=root/('image-'+hashlib.sha256(data).hexdigest());folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    image=folder/'source.png'
    with Image.open(path) as original:original.convert('RGB').save(image)
    image.chmod(0o600)
    if image.stat().st_size>8_000_000:raise ValueError('image_size_limit')
    raw=subprocess.run([str(ocr),str(image)],capture_output=True,text=True,timeout=45,check=True)
    blocks=json.loads(raw.stdout)
    if not blocks:raise ValueError('image_unreadable')
    blocks=recover_labels(blocks,image,ocr)
    text=ocr_text(blocks)
    if len(text)<20 or len(text)>100_000:raise ValueError('image_text_limit')
    parsed=market_passages(blocks)
    original={'id':'image_ocr_raw','text':'OCR metni; sayfa görüntüsüyle kontrol edilmelidir:\n'+text}
    market,passages=parsed if parsed else (None,[original])
    body='\n\n'.join(p['text'] for p in passages)
    return {'body':body,'passages':[original,*passages] if parsed else passages,'images':[str(image)],
      **({'market_data':market} if market else {}),'coverage':{'complete':True,'page_count':1,'pages':[{'page':1,'mode':'image_ocr_visual','characters':len(text),'tables':2 if parsed else 0}]}}

if __name__=='__main__':
    try:print(json.dumps(read_image(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]),pathlib.Path(sys.argv[3])),ensure_ascii=False))
    except Exception as e:
        reason=str(e) if isinstance(e,ValueError) and re.fullmatch('image_[a-z_]+',str(e)) else 'image_extraction_failed'
        print(json.dumps({'error':reason}),file=sys.stderr);sys.exit(1)
