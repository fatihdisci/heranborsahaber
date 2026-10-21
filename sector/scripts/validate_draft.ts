// Local deterministic preflight. Source text stays in stdin; no network calls.
import {validateDraft,numericIssues} from '../src/editorial';
let input='';for await(const chunk of process.stdin){input+=chunk;if(input.length>4_000_000)throw Error('input_limit');}
try {
 const {draft,documents}=JSON.parse(input);
 const issues=numericIssues(draft,documents);
 try{validateDraft(draft,documents);}catch(e){issues.push(e instanceof Error?e.message:'invalid_draft');}
 process.stdout.write(JSON.stringify([...new Set(issues)]));
}catch{process.stdout.write(JSON.stringify(['invalid_validation_input']));}
