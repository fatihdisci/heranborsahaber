"""Install only this project's service. Never restart the main Hermes gateway."""
import json,os,pathlib,plistlib,shutil,subprocess,time,sys
source=pathlib.Path(__file__).resolve().parents[1]
runtime=pathlib.Path.home()/'Library/Application Support/sector-haber'
app=runtime/'app';app.mkdir(parents=True,exist_ok=True)
pdf_python=runtime/'pdf-venv/bin/python'
if not pdf_python.exists():
    subprocess.run([sys.executable,'-m','venv',str(runtime/'pdf-venv')],check=True)
    subprocess.run([str(pdf_python),'-m','pip','install','-r',str(source/'requirements-pdf.txt')],check=True)
domain=f'gui/{os.getuid()}'
if '--update' in sys.argv:
    subprocess.run(['launchctl','bootout',domain+'/com.sectorhaber.news'],capture_output=True)
    deadline=time.monotonic()+150
    while subprocess.run(['launchctl','print',domain+'/com.sectorhaber.news'],capture_output=True).returncode==0:
        if time.monotonic()>deadline:raise RuntimeError('previous_sector_service_still_stopping')
        time.sleep(0.5)
for name in ['src','scripts','assets','migrations']:
    shutil.copytree(source/name,app/name,dirs_exist_ok=True)
for name in ['sources.json','package.json','package-lock.json']:
    shutil.copy2(source/name,app/name)
subprocess.run(['npm','ci','--omit=dev','--ignore-scripts'],cwd=app,check=True)
node=shutil.which('node')
if not node:raise RuntimeError('node_required')
logs=runtime/'logs';logs.mkdir(exist_ok=True)
plist=pathlib.Path.home()/'Library/LaunchAgents/com.sectorhaber.news.plist'
payload={'Label':'com.sectorhaber.news','ProgramArguments':[node,str(app/'node_modules/tsx/dist/cli.mjs'),str(app/'scripts/local_service.ts')],
 'WorkingDirectory':str(app),'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':30,'ExitTimeOut':120,
 'EnvironmentVariables':{'HOME':str(pathlib.Path.home()),'PATH':str(pathlib.Path(node).parent)+':/opt/homebrew/bin:/usr/bin:/bin','NODE_NO_WARNINGS':'1'},
 'StandardOutPath':str(logs/'service.log'),'StandardErrorPath':str(logs/'service.error.log')}
plist.parent.mkdir(exist_ok=True);plist.write_bytes(plistlib.dumps(payload));plist.chmod(0o644)
subprocess.run(['launchctl','bootstrap',domain,str(plist)],check=True)
print('SECTOR HABER service installed. Existing Hermes gateway unchanged.')
