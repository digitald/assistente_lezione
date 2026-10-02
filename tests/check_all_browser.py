"""Esegue i cinque collaudi su archivi temporanei; richiede Node, Playwright e Edge."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TESTS = ('check_browser.cjs', 'check_notes_browser.cjs', 'check_profile_browser.cjs',
         'check_workspace_browser.cjs', 'check_quickstart_browser.cjs')


def main():
    node = shutil.which('node')
    if not node:
        raise SystemExit('Node non trovato nel PATH. Serve anche Playwright con Edge.')
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', 8877)) == 0:
            raise SystemExit('Porta di prova 8877 occupata: chiudi il precedente server di collaudo.')
    (ROOT / 'test-artifacts').mkdir(exist_ok=True)
    for test in TESTS:
        server = subprocess.Popen([sys.executable, 'tests/browser_server.py'], cwd=ROOT,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError('Il server temporaneo non si è avviato.')
                try:
                    urllib.request.urlopen('http://127.0.0.1:8877/api/state', timeout=1).close()
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Timeout del server temporaneo.')
            subprocess.run([node, 'tests/' + test], cwd=ROOT, check=True, timeout=120)
        finally:
            server.terminate()
            server.wait(timeout=10)


if __name__ == '__main__':
    main()
