import test from 'node:test';
import assert from 'node:assert/strict';
import {topicScore,MIN_DRAFT_IMPORTANCE} from '../src/editorial';
import {quota} from '../src/pipeline';
import {localDatabase} from '../src/local-adapters';
import {readFile} from 'node:fs/promises';
import type {Env} from '../src/types';
test('broader economic coverage includes share transactions, banks, FX and earnings but excludes trading-data noise',()=>{
 for(const title of ['Borsa İstanbul’da geri alım yapan şirketler','Pay alım satım bildirimi','Bankalarda kredi hacmi yükseldi','Mevduat faizlerinde yeni dönem','Döviz rezervleri açıklandı','TAV net kârını açıkladı','Nasdaq stocks rise','BIST temettü takvimi','Faiz indirimi bekleniyor'])assert(topicScore(title).score>=60,title);
 for(const title of ['Anlık hisse verisi AKD kurum dağılımı','Magazin gündemi','Günlük hisse önerileri'])assert.equal(topicScore(title).score,0,title);
 assert.equal(MIN_DRAFT_IMPORTANCE,50);
});
test('daily quota honors 240 candidates beyond old hidden 100 cap, without exceeding configured budget',async()=>{
 const DB=await localDatabase(':memory:',await readFile('migrations/0001_sector.sql','utf8'));
 const env={DB,AI_DAILY_DRAFT_LIMIT:'240'} as Env;
 for(let i=0;i<240;i++)assert.equal(await quota(env),true,`candidate ${i+1}`);
 assert.equal(await quota(env),false);assert.equal(await quota({...env,AI_DAILY_DRAFT_LIMIT:'0'}),false);
 assert.equal(await quota({...env,AI_DAILY_DRAFT_LIMIT:'invalid'}),false);
});

import {numericTokens} from '../src/editorial';
test('calendar dates match written dates without treating date as a monetary number',()=>{
 assert.deepEqual(numericTokens('19.10.2026 tarihinde 1.155.000 TL'),numericTokens('19 Ekim 2026 tarihinde 1.155.000 TL'));
});

test('compound thousands retain their complete quantity',()=>{assert.deepEqual(numericTokens('814 bin 459 pay'),['814459']);});
