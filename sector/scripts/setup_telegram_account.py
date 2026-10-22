"""Interactive local setup. Never put a login code or API hash in chat or argv."""
import os,pathlib,subprocess,sys

def main():
    if not sys.stdin.isatty():raise SystemExit('Bu kurulum Mac mini Terminal uygulamasında açılmalıdır.')
    os.umask(0o077)
    app=pathlib.Path(__file__).resolve().parents[1]
    root=pathlib.Path.home()/'Library/Application Support/sector-haber/telegram-account'
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    python=root/'venv/bin/python'
    if not python.exists():subprocess.run([sys.executable,'-m','venv',str(python.parent.parent)],check=True)
    subprocess.run([str(python),'-m','pip','install','--disable-pip-version-check','-r',str(app/'requirements-telegram.txt')],check=True)
    subprocess.run([str(python),str(app/'scripts/telegram_account.py'),'setup'],check=True)
if __name__=='__main__':
    try:main()
    except subprocess.CalledProcessError:
        raise SystemExit('Kurulum tamamlanamadı. Yukarıdaki hatayı kontrol edip bağlantı dosyasını yeniden açabilirsin.')
    except (KeyboardInterrupt,EOFError):
        raise SystemExit('Kurulum iptal edildi; yeniden açarak devam edebilirsin.')
