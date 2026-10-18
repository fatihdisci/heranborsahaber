"""Small, auditable Turkish display rewrites after verbatim evidence validation.

No free-form model paraphrase is accepted. Unmatched sentences and all conditions
remain intact. Facts and original quotes are retained in the stored result.
"""
import re

NUMBER = r'\d+(?:[.,]\d+)*'
PATTERNS = [
    (rf'politika faizini yüzde {NUMBER} olarak belirlediğini', 'belirlediğini', 'belirledi'),
    (rf'politika faizini yüzde {NUMBER} düzeyinde sabit tuttuğunu', 'tuttuğunu', 'tuttu'),
    (rf'{NUMBER} (?:milyon|milyar) (?:TL|lira|dolar|euro) tutarında sözleşme imzaladığını', 'imzaladığını', 'imzaladı'),
    (rf'{NUMBER} (?:milyon|milyar) (?:TL|lira|dolar|euro) tutarında yatırım yapmayı planladığını', 'planladığını', 'planlıyor'),
]


def rewrite_sentence(text, actor=None, quoted=False):
    if quoted or any(c in text for c in '"“”«»'):
        return text
    rewritten = text
    if actor:
        # Fullmatch prevents deletion of an appended condition, period or denial.
        for pattern, old, new in PATTERNS:
            match = re.fullmatch(re.escape(actor) + r',? (' + pattern + r') (?:açıkladı|bildirdi)\.', text)
            if match:
                clause = match[1][:-len(old)] + new
                rewritten = actor + ': ' + clause[0].upper() + clause[1:] + '.'
                break
    # Percentage points are a different unit. Literal quotations are untouched.
    rewritten = re.sub(r'\byüzde (' + NUMBER + r')(?![\d.,])\b(?!\s+puan)', r'%\1', rewritten)
    # Defensive invariant: no numerical token may be changed or deleted.
    if re.findall(NUMBER, text) != re.findall(NUMBER, rewritten):
        return text
    return rewritten


def display_article(headline, facts, options=None, speaker=None):
    from .normalizer import norm
    options = options or {}
    trim = lambda value: norm(value).rstrip('.!? ')
    matching = next((f for f in facts if trim(f['text']) == trim(headline)), None)
    def render(f):
        if SOURCE_VOICE.search(f['text']):
            if not speaker:
                from .schema import ValidationError
                raise ValidationError('unattributed_source_voice')
            return attributed_fund_sentence(f['text'],speaker,bool(f.get('quote')))
        return rewrite_sentence(f['text'], f['actor'], bool(f.get('quote')))
    title = render(matching).rstrip('.') if matching else headline
    body = [render(f) for f in facts if trim(f['text']) != trim(headline)]
    # Even "shorten" retains every selected fact, including conditions/denials.
    return title + ('\n\n' + '\n\n'.join(body) if body else '')


SOURCE_VOICE = re.compile(r'\b(?:fon(?:umuz|larımız|um|larım)\w*|şirketimiz\w*|portföyümüz\w*|biz(?:im|e|den)?|tamamladık|gerçekleştirdik|duyuruyoruz)\b', re.I)


def article_speaker(title, passages, facts=()):
    """Bind a named source-title subject to an explicit statement introduction."""
    match=re.match(r"^([\wÇĞİÖŞÜçğıöşü][\wÇĞİÖŞÜçğıöşü .&-]{1,64})['’](?:den|dan|nin|nın|nun|nün)\b",title,re.I)
    if not match:return None
    name=match[1].strip()
    attribution=re.compile(re.escape(name)+r'\s+yaptığı açıklamada şu ifadeleri kullandı\s*:',re.I)
    selected=[f['text'] for f in facts if SOURCE_VOICE.search(f['text'])]
    for passage in passages:
        intro=attribution.search(passage)
        if not intro:continue
        # Bind each selected first-person sentence to this named quotation only.
        block=re.match(r'\s*["“](.*?)["”]',passage[intro.end():],re.S)
        if block and selected and all(text in block[1] for text in selected):return name
    return None


def attributed_fund_sentence(text,speaker,quoted=False):
    """Exact statement templates only: preserve totals, dates and numerical tokens."""
    if not speaker:return None
    if not quoted:
        total=re.fullmatch(r'(?:Bununla birlikte )?tasfiye sürecinde bulunan, toplam büyüklüğü ('+NUMBER+r') TL tutarındaki (\d+) fonumuzun tasfiyesi başarıyla gerçekleştirilmiştir\.',text,re.I)
        if total:
            return f'{speaker}, {total[1]} TL büyüklüğündeki {total[2]} fonun tasfiyesinin tamamlandığını açıkladı.'
        today=re.fullmatch(r'Bugün tasfiye edilen fonlarımızın toplam büyüklüğü ('+NUMBER+r') TL toplam yatırımcı sayısı ise (\d+) olarak gerçekleşmiştir\.',text,re.I)
        if today:
            return f'{speaker}: Bugün tasfiye edilen fonların büyüklüğü {today[1]} TL; toplam yatırımcı sayısı {today[2]}.'
    return speaker+' açıklamasında: “'+text+'”'
