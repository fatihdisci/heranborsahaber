"""Stage, validate and roll back only the isolated KAP collector.

No credentials, Telegram polling, preference changes or history replay.
"""
import pathlib,platform,shutil,subprocess,sys
from install_local import Installer

def main():
    if platform.system()!='Darwin':raise RuntimeError('local_installer_requires_macos')
    node=shutil.which('node')
    if not node:raise RuntimeError('node_required')
    home=pathlib.Path.home()
    Installer(pathlib.Path(__file__).resolve().parents[1],home/'Library/Application Support/sector-haber/kap',home/'Library/LaunchAgents/com.sectorhaber.kap.plist',node,run=subprocess.run,collector=True).install('--update' in sys.argv)
    print('ENDEKS KAP collector verified and activated. Preferences, cursors and source records preserved.')

if __name__=='__main__':main()
