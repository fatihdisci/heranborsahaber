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


def display_article(headline, facts, options=None):
    from .normalizer import norm
    options = options or {}
    trim = lambda value: norm(value).rstrip('.!? ')
    matching = next((f for f in facts if trim(f['text']) == trim(headline)), None)
    render = lambda f: rewrite_sentence(f['text'], f['actor'], bool(f.get('quote')))
    title = render(matching).rstrip('.') if matching else headline
    body = [render(f) for f in facts if trim(f['text']) != trim(headline)]
    # Even "shorten" retains every selected fact, including conditions/denials.
    return title + ('\n\n' + '\n\n'.join(body) if body else '')
