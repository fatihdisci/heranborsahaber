type SignalHost={on:(signal:'SIGTERM'|'SIGINT',listener:()=>void)=>unknown;off:(signal:'SIGTERM'|'SIGINT',listener:()=>void)=>unknown};

/** Interruptible service waits. A stop signal clears outstanding timers immediately. */
export function createShutdownController(host:SignalHost){
 let stopping=false;
 const waiters=new Set<()=>void>();
 const stop=()=>{if(stopping)return;stopping=true;for(const wake of [...waiters])wake();};
 host.on('SIGTERM',stop);host.on('SIGINT',stop);
 const pause=(ms:number):Promise<void>=>new Promise(resolve=>{
  if(stopping){resolve();return;}
  let finished=false;
  const finish=()=>{if(finished)return;finished=true;clearTimeout(timer);waiters.delete(finish);resolve();};
  const timer=setTimeout(finish,Math.max(0,ms));waiters.add(finish);
  if(stopping)finish();
 });
 return {pause,stop,dispose:()=>{host.off('SIGTERM',stop);host.off('SIGINT',stop);},get stopping(){return stopping;}};
}

/** Always release both the lock handle and its filesystem marker, even on early exit. */
export async function withServiceLock<T>(lock:{close:()=>Promise<unknown>},remove:()=>Promise<unknown>,work:()=>Promise<T>):Promise<T>{
 try{return await work();}
 finally{try{await lock.close();}finally{await remove().catch(()=>{});}}
}
