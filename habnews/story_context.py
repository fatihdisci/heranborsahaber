"""Narrow source proofs for a central development, never title-only inference."""
import re
from .normalizer import norm

def ipo_application_heading(title, passages):
    """Bind an issuer's reapplication heading to a complete explicit body report.

    Subsidiary/shareholder relations remain in the source; no shareholder is
    substituted for the issuer. Denials, approvals and conditions do not match.
    """
    heading=re.fullmatch(r"([\wÇĞİÖŞÜçğıöşü& .-]{2,80}) halka arz için SPK['’]ya yeniden başvurdu[.]?",title)
    if not heading:return None
    issuer=heading[1]
    regulator=r"(?:Sermaye Piyasası Kuruluna \(SPK\)|SPK['’]ya)"
    company=re.escape(issuer)+r"(?: [\w&.-]+){0,12}"
    report=(r"[\w ()&.’'-]+, yüzde \d+(?:[.,]\d+)? oranında pay sahibi olduğu "
            +company+r" A\.Ş\.['’]nin halka arz için "+regulator+r" yeniden başvurduğunu duyurdu\.")
    direct=re.escape(issuer)+r",? halka arz için "+regulator+r" yeniden başvurdu\."
    from .schema import complete_source_sentence
    for passage in passages:
        lines=passage.splitlines()
        # The heading cannot prove itself.
        body='\n'.join(lines[1:]) if lines and norm(lines[0])==norm(title) else passage
        for pattern in (report,direct):
            for match in re.finditer(pattern,body):
                if complete_source_sentence(match[0],body):
                    return {'headline':title,'issuer':issuer,'support':match[0]}
    return None
