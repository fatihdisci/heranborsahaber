import {xClient} from './x_client';
let input='';for await(const part of process.stdin){input+=part;if(input.length>4096)process.exit(1);}
try{const user=await xClient(JSON.parse(input)).identity();if(user.username.toLowerCase()!=='endeks_haber')throw Error('x_wrong_account');console.log('verified');}
catch(e){console.log(e instanceof Error&&/^x_[a-z_0-9]+$/.test(e.message)?e.message:'x_verification_failed');process.exit(1);}
