import importlib.util,time,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('sector_job',Path(__file__).parents[1]/'scripts/hermes_job.py')
job_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(job_module)

class HermesJobContract(unittest.TestCase):
    def job(self):return {'id':'test','provider':'openai-codex','model':'gpt-6-luna','effort':'high','allowed_tools':[],'deadline':time.time()+600,'prompt':'Grounded editor','schema':{},'documents':[],'audit_prompt':'Check facts'}
    def test_no_paid_provider_or_tools_can_run(self):
        for change in [{'provider':'openai-api'},{'allowed_tools':['terminal']},{'effort':'low'}]:
            with patch.object(job_module,'call') as call:
                with self.assertRaises(RuntimeError):job_module.main(self.job()|change)
                call.assert_not_called()
    def test_verified_draft_uses_two_subscription_turns(self):
        with patch.object(job_module,'call',side_effect=[{'headline':'source'}, {'supported':True,'issues':[]}]) as call:
            result=job_module.main(self.job());self.assertEqual(call.call_count,2);self.assertEqual(result['runtime']['calls'],2)
    def test_semantic_failure_has_one_bounded_repair(self):
        with patch.object(job_module,'call',side_effect=[{'headline':'bad'},{'supported':False,'issues':['condition lost']},{'headline':'fixed'},{'supported':True,'issues':[]}]) as call:
            result=job_module.main(self.job());self.assertEqual(call.call_count,4);self.assertEqual(result['draft']['headline'],'fixed')
    def test_persistent_failure_never_loops_or_changes_provider(self):
        with patch.object(job_module,'call',side_effect=[{}, {'supported':False,'issues':['unsupported']},{}, {'supported':False,'issues':['unsupported']}]) as call:
            result=job_module.main(self.job());self.assertEqual(call.call_count,4);self.assertFalse(result['audit']['supported']);self.assertEqual(result['runtime']['fallback_count'],0)
    def test_expired_job_does_not_spend_a_turn(self):
        with patch.object(job_module,'call') as call:
            with self.assertRaises(RuntimeError):job_module.main(self.job()|{'deadline':0})
            call.assert_not_called()
    def test_caption_overflow_is_rewritten_and_reaudited_without_truncation(self):
        long={'headline':'Başlık','body':'Uzun içerik '*120,'hashtags':['#Ekonomi','#Finans']}
        short={'headline':'Başlık','body':'Önemli bilgi korunmuş kısa metin.','hashtags':['#Ekonomi','#Finans']}
        with patch.object(job_module,'call',side_effect=[long,{'supported':True,'issues':[]},short,{'supported':True,'issues':[]}]) as call:
            result=job_module.main(self.job());self.assertEqual(call.call_count,4);self.assertEqual(result['draft'],short)
        self.assertTrue(job_module.presentation_issues({'headline':'🌍'*510,'body':'Açıklama','hashtags':['#Ekonomi','#Finans']}))

    def test_json_fence_handling_does_not_accept_prose(self):
        self.assertEqual(job_module.decode('```json\n{"başlık":"Haber"}\n```'),{'başlık':'Haber'})
        with self.assertRaises(ValueError):job_module.decode('Result is not a JSON object')

if __name__=='__main__':unittest.main()
