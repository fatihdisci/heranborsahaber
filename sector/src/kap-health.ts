// Queue review is attention on retained content, not a collector outage.
export function kapDeliveryHealth(state:string){return {ok:!['uncertain','evidence_failed'].includes(state),attention:state==='needs_review'?'content_review':undefined};}
