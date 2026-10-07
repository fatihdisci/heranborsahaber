from pathlib import Path
import yaml
ROOT=Path(__file__).parents[1]

def test_no_old_mounts_or_cloud_resources():
    doc=yaml.safe_load((ROOT/'deploy/compose.yaml').read_text())
    assert doc['name']=='habnews'
    serialized=(ROOT/'deploy/compose.yaml').read_text()
    for forbidden in ('2127440b-97f6-4d54-b9b8-2bc0a461130a','heranborsa-command-media','/Users/','docker.sock','heranborsacode','TELEFLOW_MASTER_KEY','CLOUDFLARE_API_TOKEN'):
        assert forbidden not in serialized
    assert not any('ports' in s for s in doc['services'].values())
    assert doc['services']['collector']['network_mode']=='none'
    assert doc['networks']['provider_internal']['internal'] is True
    assert doc['networks']['telegram_internal']['internal'] is True

def test_credentials_not_shared_to_runner_or_collector():
    doc=yaml.safe_load((ROOT/'deploy/compose.yaml').read_text())
    runner=' '.join(doc['services']['runner']['volumes']);collector=' '.join(doc['services']['collector']['volumes'])
    assert 'telegram.json' not in runner+collector
    assert '/data' not in runner
    assert '/auth' not in collector

def test_provider_proxy_no_other_models_or_publish_hosts():
    s=(ROOT/'deploy/provider-squid.conf').read_text()
    assert 'provider_hosts dstdomain chatgpt.com auth.openai.com' in s
    assert 'http_access deny all' in s
    assert 'api.openai.com' not in s and 'openrouter.ai' not in s

def test_revision_and_dependency_pins():
    docker=(ROOT/'deploy/Dockerfile').read_text()
    assert 'dd0e4ab81abccf7df5b11c6c16853d5e5de9db69' in docker
    assert 'uv sync --frozen' in docker and '@sha256:' in docker
    s=yaml.safe_load((ROOT/'deploy/hermes-config.yaml').read_text())
    assert s['model']=={'provider':'openai-codex','default':'gpt-6-luna'}
    assert not s['fallback_providers'] and not s['compression']['enabled']
    assert s['agent']['api_max_retries']==1
    assert all(v['provider']=='openai-codex' and v['model']=='gpt-6-luna' for v in s['auxiliary'].values())

def test_foreign_sqlite_never_adopted(tmp_path):
    import sqlite3,pytest
    from habnews.db import DB
    target=tmp_path/'habnews.sqlite';conn=sqlite3.connect(target);conn.execute('CREATE TABLE unrelated(id)');conn.commit();conn.close()
    with pytest.raises(ValueError,match='not_a_habnews'):DB(target)
    assert sqlite3.connect(target).execute("SELECT count(*) FROM sqlite_master WHERE name LIKE 'habnews_%'").fetchone()[0]==0

def test_old_profile_database_path_denied(tmp_path):
    import pytest
    from habnews.db import DB
    for path in (tmp_path/'.hermes/habnews.sqlite',tmp_path/'state.db',tmp_path/'heranborsacode/habnews.sqlite'):
        with pytest.raises(ValueError,match='namespace_denied'):DB(path)

def test_secrets_excluded_from_build_context():
    ignores=(ROOT/'.dockerignore').read_text().splitlines()
    assert 'private' in ignores and 'state' in ignores and '.env' in ignores and '**/auth.json' in ignores
    assert '.dockerignore' in (ROOT/'deploy/install-linux.sh').read_text()
