import importlib.util,pathlib,tempfile,unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('panel_install',pathlib.Path(__file__).parents[1]/'scripts/install_panel.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PanelInstall(unittest.TestCase):
    def test_menu_rollback_preserves_previous_owner_menu(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);panel=root/'miniapp';panel.mkdir();(root/'secrets.json').write_text(json.dumps({'TELEGRAM_CHAT_ID':'7'}));(panel/'config.json').write_text(json.dumps({'url':'https://example.workers.dev'}))
            previous={'type':'commands'}
            with patch.object(m,'ROOT',root),patch.object(m,'PANEL',panel),patch.object(m,'api',return_value=previous) as call:
                m.menu(True);self.assertEqual(call.call_args.args[1]['menu_button']['type'],'web_app')
                m.menu(False);self.assertEqual(call.call_args.args[1],{'chat_id':'7','menu_button':previous})
    def test_only_panel_launch_agent_is_stopped(self):
        with patch.object(m.subprocess,'run') as call:
            m.bootout();self.assertIn('com.endekshaber.panel',call.call_args.args[0][-1]);self.assertNotIn('com.sectorhaber.news',str(call.call_args))
    def test_missing_config_does_not_stop_services(self):
        with tempfile.TemporaryDirectory() as d,patch.object(m,'PANEL',pathlib.Path(d)),patch.object(m,'bootout') as stop:
            with self.assertRaisesRegex(RuntimeError,'panel_config_required'):m.install(pathlib.Path(d))
            stop.assert_not_called()
if __name__=='__main__':unittest.main()
