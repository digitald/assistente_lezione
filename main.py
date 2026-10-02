"""Avvio web predefinito; --desktop conserva l'interfaccia precedente."""

import os
import sys
import argparse
from version import __version__

# I messaggi con simboli non devono interrompere le operazioni su Windows.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

try:
    import config
except ModuleNotFoundError as exc:
    if exc.name != "config":
        raise
    import config_template as config
    sys.modules["config"] = config

if __name__ == "__main__":
    if "--desktop" not in sys.argv:
        parser = argparse.ArgumentParser(description="Assistente Lezione web locale")
        parser.add_argument("--version", action="version", version=__version__)
        parser.add_argument("--demo", action="store_true")
        parser.add_argument("--port", type=int, default=8765)
        parser.add_argument("--no-browser", action="store_true")
        args = parser.parse_args()
        from web_app import run
        run(demo=args.demo, port=args.port, open_browser=not args.no_browser)
        sys.exit(0)
    parser = argparse.ArgumentParser(description="Assistente Lezione")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--desktop", action="store_true", help="Avvia l'interfaccia Tkinter precedente")
    parser.add_argument("--demo", action="store_true", help="Prova simulata senza microfono o API")
    args = parser.parse_args()
    from tkinter import messagebox
    from ai_client import AIClient
    from audio_worker import TranscriptionWorker
    from gui import launch_gui
    if args.demo:
        from pathlib import Path
        from demo_client import DemoAIClient
        demo_dir = Path(__file__).resolve().parent / "demo_data"
        config.NOTES_DIR = str(demo_dir / "notes")
        config.TRANSCRIPTS_DIR = str(demo_dir / "transcripts")
    # 1. Crea le cartelle necessarie
    os.makedirs(config.NOTES_DIR, exist_ok=True)
    os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)

    # 2. Controlla la API Key
    api_key = os.getenv("OPENAI_API_KEY", config.OPENAI_API_KEY)
    if not args.demo and (not api_key or api_key == "sk-..."):
        error_msg = "API key di OpenAI non trovata o non configurata in config.py"
        print(f"❌ {error_msg}")
        try:
            messagebox.showerror("Errore API Key", error_msg)
        except Exception:
            pass
        sys.exit(1)

    # 3. Inizializza i componenti
    ai_client = DemoAIClient() if args.demo else AIClient(api_key)
    
    # Crea il worker usando la nuova classe semplificata
    worker = None if args.demo else TranscriptionWorker(ai_client)

    # 4. Avvia il worker in un thread in background
    if worker is not None:
        worker.start()

    # 5. Avvia l'interfaccia grafica (GUI)
    print("🚀 Avvio dell'Assistente Lezione...")
    launch_gui(ai_client, demo=args.demo, worker=worker)
