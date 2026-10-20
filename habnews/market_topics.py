"""Current investor-protection topics, kept separate from issuer identities."""
import re

FUND_CRISIS=re.compile(r'fon kriz|fon vurgun|sorunlu fon|olağanüstü tasfiye',re.I)
SETTLEMENT=re.compile(r'\bpblk\b|takas kesinli[ğg]i|muaccel alacak|yatırımcı alacak|yatırımcı tazmin',re.I)
FINANCIAL_CONTEXT=re.compile(r'\bfon\w*|yatırımcı|\bmkk\b|takas|tasfiye|alacak|bloke|blokaj|geri ödeme|sermaye piyasası',re.I)
FOREIGN_FUND=re.compile(r'\b(?:abd|amerikan|çin|japonya|avrupa|ingiltere)\b.{0,30}\b(?:yatırım )?fon',re.I)
FOCUS_ACTION=re.compile(r'karar|kabul|kanun|teklif|düzenleme|ödeme|iade|itiraz|bloke|blokaj|alacak|temerrüt|hak sahip',re.I)

def investor_focus(text):
    # PBLK is treated only as a supplied market-topic token, never an issuer or
    # a legal entitlement. Its meaning and consequences must come from source.
    return bool(FUND_CRISIS.search(text) or SETTLEMENT.search(text) and FINANCIAL_CONTEXT.search(text))
