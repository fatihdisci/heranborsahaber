// Local deterministic preflight. Source text stays in stdin; no network calls.
import {draftCard} from '../src/card';
import {CARD_LAYOUTS} from '../src/card-layout';
import {repairDraftStyle} from '../src/style';
import {validateDraft,numericIssues} from '../src/editorial';
import {repairEvidenceReferences,evidenceIssues} from '../src/evidence-references';
let input='';for await(const chunk of process.stdin){input+=chunk;if(input.length>4_000_000)throw Error('input_limit');}
try {
 const {draft,documents}=JSON.parse(input);
 if(process.argv.includes('--normalize')){process.stdout.write(JSON.stringify(repairDraftStyle(repairEvidenceReferences(draft,documents),documents)));process.exit(0);}
 const issues=[...evidenceIssues(draft,documents),...numericIssues(draft,documents)];
 try{if(validateDraft(draft,documents).verification==='needs_review')issues.push('Taslakta çözülmemiş belirsizlik var. Etkilenen olguyu kaynaklardan çöz veya doğrulanabilir çekirdek haberi seç. Çelişkiyi tahminle düzeltme; aktarılan olguyu hâlâ etkiliyorsa uncertainties korunsun. Yalnız hiç aktarılmayan ikincil alanın kaynak sorunuysa source_notes içinde kaydet.');}catch(e){issues.push(e instanceof Error?e.message:'invalid_draft');}
 if(draft?.card_data&&['circuit','institutional','akd','volume','broker_flow','custody'].includes(draft.template))try{for(const layout of CARD_LAYOUTS)draftCard(draft,[],'',false,'navy',layout);}catch{issues.push('Kart tablosu veya metrik değeri görsele sığmıyor. Sayı ve birimleri değiştirme; eşdeğer tam sayısal yazım kullan, kurum unvanını kaynağa sadık kısa adıyla yaz veya ikincil ayrıntıyı çıkar.');}
 process.stdout.write(JSON.stringify([...new Set(issues)]));
}catch{process.stdout.write(JSON.stringify(['invalid_validation_input']));}
