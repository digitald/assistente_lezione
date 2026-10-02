@echo off
setlocal
cd /d "%~dp0"
py -3.12 -c "import struct; assert struct.calcsize('P') == 8, 'Serve Python a 64 bit'"
if errorlevel 1 (
  echo Installa Python 3.12 a 64 bit da python.org con il launcher py.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 goto errore
)
".venv\Scripts\python.exe" -c "import sys,struct; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8, 'Ambiente esistente incompatibile: usa una nuova cartella'"
if errorlevel 1 goto errore
".venv\Scripts\python.exe" -m pip install -r requirements-lock.txt
if errorlevel 1 goto errore
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto errore
if not exist config.py copy /-Y config_template.py config.py >nul
if errorlevel 1 goto errore
echo Installazione completata. Apri avvia_prova.cmd per la demo o avvia_lezione.cmd.
echo Per OpenAI configura la chiave in config.py. Per GPU consulta docs\INSTALLAZIONE_ALTRO_PC.md.
pause
exit /b 0
:errore
echo Installazione non completata. Leggi il messaggio precedente. Nessuna configurazione privata viene sovrascritta.
pause
exit /b 1
