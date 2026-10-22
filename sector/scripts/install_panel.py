"""Isolated read-only Mini App sync. Never restarts news/KAP/Hermes.
Requires an already deployed panel and private config.json in the panel runtime.
"""
import json,os,pathlib,plistlib,shutil,subprocess,sys,time,uuid,urllib.request,re
ROOT=pathlib.Path.home()/'Library/Application Support/sector-haber'
PANEL=ROOT/'miniapp'
LABEL='com.endekshaber.panel'
PLIST=pathlib.Path.home()/'Library/LaunchAgents'/f'{LABEL}.plist'

def api(method,body):
    secrets=json.loads((ROOT/'secrets.json').read_text())
    req=urllib.request.Request('https://api.telegram.org/bot'+secrets['TELEGRAM_BOT_TOKEN']+'/'+method,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=15) as r: result=json.load(r)
    if not result.get('ok'):raise RuntimeError('panel_menu_failed')
    return result['result']

def cloud(enable):
    config=json.loads((PANEL/'config.json').read_text())
    request=urllib.request.Request(config['url'].rstrip('/')+'/sync/'+('enable' if enable else 'disable'),method='PUT',headers={'Authorization':'Bearer '+config['syncToken'],'User-Agent':'ENDEKS-Panel/1.0'})
    with urllib.request.urlopen(request,timeout=15) as response:
        if response.status!=200:raise RuntimeError('panel_switch_failed')

def bootout():
    service=f'gui/{os.getuid()}/{LABEL}'
    status=subprocess.run(['launchctl','print',service],capture_output=True,text=True)
    match=re.search(r'^\s*pid = (\d+)\s*$',status.stdout or '',re.MULTILINE)
    pid=int(match[1]) if match else None
    subprocess.run(['launchctl','bootout',service],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    # launchd may return before the old sync process has drained its HTTP call.
    # Re-registering immediately can fail with EIO, including during rollback.
    for _ in range(90):
        loaded=subprocess.run(['launchctl','print',service],capture_output=True).returncode==0
        alive=False
        if pid:
            try:os.kill(pid,0);alive=True
            except ProcessLookupError:pass
        if not loaded and not alive:return
        time.sleep(.5)
    raise RuntimeError('panel_stop_timeout')


def menu(enable):
    secrets=json.loads((ROOT/'secrets.json').read_text());chat=secrets['TELEGRAM_CHAT_ID']
    previous=PANEL/'previous-menu.json'
    if enable:
        if not previous.exists():previous.write_text(json.dumps(api('getChatMenuButton',{'chat_id':chat})));previous.chmod(0o600)
        url=json.loads((PANEL/'config.json').read_text())['url']
        button={'type':'web_app','text':'Haber paneli','web_app':{'url':url}}
    else:
        if not previous.exists():return
        button=json.loads(previous.read_text())
    api('setChatMenuButton',{'chat_id':chat,'menu_button':button})

def install(source):
    PANEL.mkdir(parents=True,exist_ok=True,mode=0o700)
    if not (PANEL/'config.json').exists():raise RuntimeError('panel_config_required')
    node=pathlib.Path.home()/'.local/bin/node'
    if not node.exists():raise RuntimeError('node22_required')
    env={**os.environ,'PATH':str(node.parent)+':'+os.environ.get('PATH','')}
    if not subprocess.check_output([str(node),'--version'],env=env,text=True).startswith('v22.'):raise RuntimeError('node22_required')
    stage=PANEL/'releases'/uuid.uuid4().hex;stage.mkdir(parents=True)
    for name in ['src','scripts','miniapp']:
        shutil.copytree(source/name,stage/name,ignore=shutil.ignore_patterns('__pycache__','.wrangler','dist','.dev.vars','.env*'))
    for name in ['package.json','package-lock.json','tsconfig.json','sources.json']:
        shutil.copy2(source/name,stage/name)
    try:
        for command in [['npm','ci','--ignore-scripts'],['npm','run','check']]:
            p=subprocess.run(command,cwd=stage,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            if p.returncode:raise RuntimeError('panel_stage_validation_failed')
        p=subprocess.run([str(node),'--import','tsx','scripts/panel_sync.ts','--once'],cwd=stage,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        if p.returncode:raise RuntimeError('panel_initial_sync_failed')
    except Exception:shutil.rmtree(stage);raise
    old=PLIST.read_bytes() if PLIST.exists() else None
    plist={'Label':LABEL,'ProgramArguments':[str(node),'--import','tsx',str(stage/'scripts/panel_sync.ts')],'WorkingDirectory':str(stage),'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':30,'EnvironmentVariables':{'PATH':env['PATH']},'StandardOutPath':str(PANEL/'service.log'),'StandardErrorPath':str(PANEL/'service-error.log')}
    bootout()
    try:
        PLIST.write_bytes(plistlib.dumps(plist));PLIST.chmod(0o600)
        activated=time.time()
        subprocess.run(['launchctl','bootstrap',f'gui/{os.getuid()}',str(PLIST)],check=True,stdout=subprocess.DEVNULL)
        for attempt in range(45):
            time.sleep(1)
            health=PANEL/'health.json'
            if health.exists() and health.stat().st_mtime>=activated and json.loads(health.read_text()).get('ok'):break
        else:raise RuntimeError('panel_readiness_failed')
        subprocess.run(['launchctl','print',f'gui/{os.getuid()}/{LABEL}'],check=True,stdout=subprocess.DEVNULL)
        cloud(True)
        menu(True)
        (PANEL/'active-release').write_text(str(stage))
    except Exception:
        bootout()
        if old:
            PLIST.write_bytes(old);subprocess.run(['launchctl','bootstrap',f'gui/{os.getuid()}',str(PLIST)],stdout=subprocess.DEVNULL)
        else:PLIST.unlink(missing_ok=True)
        menu(False);raise
    print('Panel sync and owner-only menu enabled; production services untouched.')

if __name__=='__main__':
    try:
        if '--disable' in sys.argv:
            menu(False);bootout();PLIST.unlink(missing_ok=True);cloud(False);print('Previous bot menu restored. Panel sync stopped. News/KAP/Hermes unchanged.')
        else:install(pathlib.Path(__file__).resolve().parents[1])
    except Exception as e:
        print('Panel operation failed:',str(e) if isinstance(e,RuntimeError) else type(e).__name__);sys.exit(1)
