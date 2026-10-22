import importlib.util,pathlib,tempfile,unittest,time,json
from types import SimpleNamespace as N
from unittest.mock import AsyncMock,patch
spec=importlib.util.spec_from_file_location('telegram_account',pathlib.Path(__file__).parents[1]/'scripts/telegram_account.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class AccountQueries(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name);self.db=m.open_journal(self.root)
        self.value={'bot':'b0pt_bot','command':'/kurum bank of america','key':'123'}
        self.peer=N(id=7,bot=True,username='b0pt_bot')
    def tearDown(self):self.db.close();self.temp.cleanup()
    def request(self,state,sent_id=10):
        self.db.execute('INSERT INTO requests VALUES(?,?,?,?,?,?,?,?)',('123','b0pt_bot','/kurum bank of america',state,7,sent_id,None,time.time()));self.db.commit()
    def message(self,id=11,**kwargs):
        return N(**dict(dict(id=id,out=False,sender_id=7,reply_to_msg_id=10,photo=None,document=None,file=None,raw_text='Net hacim: 100 milyon TL',edit_date=None),**kwargs))
    def test_routes_are_allowlisted_and_injected_commands_fail(self):
        for bot,command in [('b0pt_bot','/kurum Ak Yatırım'),('ucretsizderinlikbot','/kurum'),('ucretsizderinlikbot','/akd ASELS'),('ucretsizderinlikbot','/takas THYAO')]:m.validate_query(dict(self.value,bot=bot,command=command))
        for bot,command in [('evil_bot','/kurum'),('b0pt_bot','/start'),('b0pt_bot','/kurum abc\n/start'),('ucretsizderinlikbot','/akd ASELS;cat')]:
            with self.assertRaises(m.QueryError):m.validate_query(dict(self.value,bot=bot,command=command))
    async def test_unknown_send_is_persisted_and_never_resent(self):
        client=N(get_entity=AsyncMock(return_value=self.peer),send_message=AsyncMock(side_effect=TimeoutError()))
        with self.assertRaisesRegex(m.QueryError,'delivery_uncertain'):await m.query(client,self.db,self.root,self.value)
        with self.assertRaisesRegex(m.QueryError,'delivery_uncertain'):await m.query(client,self.db,self.root,self.value)
        self.assertEqual(client.send_message.await_count,1)
    async def test_resume_received_messages_does_not_resend_and_completed_results_reuse(self):
        self.request('sent');client=N(get_entity=AsyncMock(return_value=self.peer),send_message=AsyncMock(),get_messages=AsyncMock(return_value=[self.message()]))
        with patch.object(m.time,'monotonic',side_effect=[0,0,0,0,9,10]),patch.object(m.asyncio,'sleep',new=AsyncMock()):
            result=await m.query(client,self.db,self.root,self.value)
        self.assertEqual(result['text'],'Net hacim: 100 milyon TL');client.send_message.assert_not_awaited()
        client.get_entity.reset_mock();again=await m.query(client,self.db,self.root,self.value)
        self.assertEqual(again,result);client.get_entity.assert_not_awaited()
    async def test_another_unfinished_query_blocks_a_new_command(self):
        self.request('sent');client=N(get_entity=AsyncMock(return_value=self.peer),send_message=AsyncMock())
        with self.assertRaisesRegex(m.QueryError,'busy'):await m.query(client,self.db,self.root,dict(self.value,key='124'))
        client.send_message.assert_not_awaited()
    def test_unrelated_replies_are_excluded_and_interleaved_command_is_ambiguous(self):
        msgs=[self.message(),self.message(12,sender_id=8),self.message(13,reply_to_msg_id=9),self.message(9)]
        self.assertEqual([v.id for v in m.candidate_messages(msgs,7,10)],[11])
        with self.assertRaisesRegex(m.QueryError,'ambiguous'):m.candidate_messages(msgs+[self.message(14,out=True)],7,10)
    async def test_changed_peer_binding_prevents_sending(self):
        self.db.execute('INSERT INTO peers VALUES(?,?)',('b0pt_bot',999));self.db.commit()
        client=N(get_entity=AsyncMock(return_value=self.peer),send_message=AsyncMock())
        with self.assertRaisesRegex(m.QueryError,'peer_invalid'):await m.query(client,self.db,self.root,self.value)
        client.send_message.assert_not_awaited()
    async def test_expired_and_flood_blocked_requests_never_send(self):
        self.db.execute("INSERT INTO limits VALUES('flood',?)",(time.time()+120,));self.db.commit()
        client=N(get_entity=AsyncMock(),send_message=AsyncMock())
        with self.assertRaisesRegex(m.QueryError,'rate_limited'):await m.query(client,self.db,self.root,self.value)
        client.get_entity.assert_not_awaited();client.send_message.assert_not_awaited()
if __name__=='__main__':unittest.main()
