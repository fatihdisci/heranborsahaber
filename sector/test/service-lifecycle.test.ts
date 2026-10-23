import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {createShutdownController,withServiceLock} from '../scripts/service-lifecycle';

for(const [signal,waitMs] of [['SIGTERM',24*3600_000],['SIGINT',15*60_000]] as const){
 test(`${signal} interrupts a long command/retry wait and releases service.lock`,async()=>{
  const signals=new EventEmitter(),shutdown=createShutdownController(signals);let closed=0,removed=0;
  const started=Date.now();
  await withServiceLock({close:async()=>{closed++;}},async()=>{removed++;},async()=>{
   const loop=async()=>{while(!shutdown.stopping)await shutdown.pause(waitMs);};
   const interrupt=setTimeout(()=>signals.emit(signal),10);
   try{await loop();}finally{clearTimeout(interrupt);}
  });
  shutdown.dispose();
  assert(Date.now()-started<1000,'shutdown should not wait for the long timer');
  assert.equal(closed,1);assert.equal(removed,1);assert.equal(shutdown.stopping,true);
 });
}

test('service lock cleanup runs when service work fails',async()=>{
 const calls:string[]=[];
 await assert.rejects(withServiceLock({close:async()=>{calls.push('close');}},async()=>{calls.push('unlink');},async()=>{throw Error('loop_failed');}),/loop_failed/);
 assert.deepEqual(calls,['close','unlink']);
});
