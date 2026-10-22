import type {Status} from './types';
export type Action='approve'|'reject'|'edit'|'defer';
export function transition(state:Status,action:Action,verification:string,expired=false):Status {
 if(expired)throw new Error('draft_expired');
 if(!['pending','deferred'].includes(state))throw new Error('draft_already_resolved');
 if(action==='approve'&&verification==='needs_review')throw new Error('unverified_draft');
 return action==='approve'?'approved':action==='reject'?'rejected':action==='defer'?'deferred':'pending';
}
export function callback(action:Action,id:string,revision:number):string {
 const value=`s:${action}:${id}:${revision}`;if(new TextEncoder().encode(value).length>64)throw new Error('callback_too_long');return value;
}
export function parseCallback(value:string):{action:Action;id:string;revision:number} {
 const m=value.match(/^s:(approve|reject|edit|defer):([a-f\d-]{36}):(\d{1,6})$/);
 if(!m)throw new Error('invalid_callback');return {action:m[1] as Action,id:m[2],revision:Number(m[3])};
}
// Legacy approval actions never publish. X requires the explicit owner-only xpost path.
export function publicationGate(_target?:string):{allowed:false;reason:string} {
 return {allowed:false,reason:'x_publishing_permanently_disabled'};
}
