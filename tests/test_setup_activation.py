import json,time
from habnews.readiness import activate_requested_setup
from habnews.telegram import ApprovalService
from habnews.approval import Approval

def prepare(db,monkeypatch):
    monkeypatch.setattr("habnews.config.sources",lambda:[{"enabled":True}])
    db.set_state('enabled','false');db.set_state('setup_activation_requested','true')
    for key in ('isolation_verified','telegram_verified','sources_verified','output_cap_verified','live_acceptance_verified'):db.set_state(key,'true')
    db.set_state('llm_state','ready');db.set_state('model_smoke',json.dumps({'status':'passed','selected_reasoning':'high','requested_model':'gpt-6-luna','tested_at':time.time()}))

def test_initial_setup_waits_for_live_callback(db,monkeypatch):
    prepare(db,monkeypatch);db.set_state('live_acceptance_verified','false')
    assert not activate_requested_setup(db);assert not db.enabled()
    assert db.state('setup_activation_requested')=='true'

def test_initial_activation_happens_once(db,monkeypatch):
    prepare(db,monkeypatch);assert activate_requested_setup(db);assert db.enabled()
    db.set_state('enabled','false');assert not activate_requested_setup(db);assert not db.enabled()

def test_stop_cancels_pending_install_activation(db,monkeypatch):
    prepare(db,monkeypatch)
    service=ApprovalService(db,Approval(db,123,123),None,777)
    service.command({'from':{'id':123},'chat':{'id':123,'type':'private'},'text':'/haber_durdur'})
    assert not activate_requested_setup(db);assert not db.enabled()
