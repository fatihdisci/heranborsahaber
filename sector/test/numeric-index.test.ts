import {test} from 'node:test';
import assert from 'node:assert/strict';
import {numericTokens} from '../src/editorial';
test('Turkish percentage prefix belongs to following value, not index identifier',()=>{
 assert.deepEqual(numericTokens('CAC 40 yüzde 1,06 artışla 7.921,68 puana çıktı.'),['40','yüzde 1,06','7.921,68 puan']);
 assert.deepEqual(numericTokens('Stoxx Europe 600 yüzde 0,92 arttı.'),['600','yüzde 0,92']);
});
