// Only the two owner-approved deployment origins can receive the sync secret.
export const PANEL_HOSTS=['endeks-haber-panel.av-fatihdisci.workers.dev','panel.discilaw.com'] as const;
export function panelURL(value:string){
 const u=new URL(value);
 if(u.protocol!=='https:'||u.username||u.password||u.port||u.pathname!=='/'||u.search||u.hash||!PANEL_HOSTS.some(h=>h===u.hostname))throw Error('panel_url_invalid');
 return u;
}
