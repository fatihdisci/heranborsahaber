"""Install only the isolated KAP collector; it has no delivery or AI credentials."""
import os,pathlib,plistlib,shutil,subprocess,time
source=pathlib.Path(__file__).resolve().parents[1]
root=pathlib.Path.home()/'Library/Application Support/sector-haber/kap'
app=root/'app';root.mkdir(parents=True,exist_ok=True,mode=0o700)
label='com.sectorhaber.kap';domain=f'gui/{os.getuid()}'
node=shutil.which('node')
if not node:raise RuntimeError('node_required')
# Stage dependencies before touching this collector's running version.
stage=root/'staging';stage.mkdir(exist_ok=True)
for name in ['src/kap','scripts']:
    dest=stage/name
    if name=='scripts':
        dest.mkdir(exist_ok=True);shutil.copy2(source/name/'kap_service.ts',dest/'kap_service.ts')
    else:shutil.copytree(source/name,dest,dirs_exist_ok=True)
for name in ['package.json','package-lock.json']:shutil.copy2(source/name,stage/name)
subprocess.run(['npm','ci','--omit=dev','--ignore-scripts'],cwd=stage,check=True)
if subprocess.run(['launchctl','print',domain+'/'+label],capture_output=True).returncode==0:
    subprocess.run(['launchctl','bootout',domain+'/'+label],check=True)
    deadline=time.monotonic()+45
    while subprocess.run(['launchctl','print',domain+'/'+label],capture_output=True).returncode==0:
        if time.monotonic()>deadline:raise RuntimeError('kap_still_stopping')
        time.sleep(.5)
previous=root/'previous-app'
if previous.exists():shutil.rmtree(previous)
if app.exists():app.rename(previous)
stage.rename(app)
logs=root/'logs';logs.mkdir(exist_ok=True)
plist=pathlib.Path.home()/'Library/LaunchAgents'/f'{label}.plist'
payload={'Label':label,'ProgramArguments':[node,str(app/'node_modules/tsx/dist/cli.mjs'),str(app/'scripts/kap_service.ts')],
 'WorkingDirectory':str(app),'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':30,'ExitTimeOut':45,
 'EnvironmentVariables':{'HOME':str(pathlib.Path.home()),'PATH':str(pathlib.Path(node).parent)+':/usr/bin:/bin','NODE_NO_WARNINGS':'1'},
 'StandardOutPath':str(logs/'collector.log'),'StandardErrorPath':str(logs/'collector.error.log')}
plist.parent.mkdir(exist_ok=True);plist.write_bytes(plistlib.dumps(payload));plist.chmod(0o600)
subprocess.run(['launchctl','bootstrap',domain,str(plist)],check=True)
print('SECTOR KAP collector installed. Delivery is not configured.')
