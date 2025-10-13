# main.py (aggiornato)

import os
import sys
import threading
from tkinter import messagebox

import config
from ai_client import AIClient
# Aggiorniamo l'import con il nuovo nome della classe
from audio_worker import TranscriptionWorker 
from gui import launch_gui

if __name__ == "__main__":
    # 1. Crea le cartelle necessarie
    os.makedirs(config.NOTES_DIR, exist_ok=True)
    os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)

    # 2. Controlla la API Key
    api_key = os.getenv("OPENAI_API_KEY", config.OPENAI_API_KEY)
    if not api_key or api_key == "sk-...":
        error_msg = "API key di OpenAI non trovata o non configurata in config.py"
        print(f"❌ {error_msg}")
        try:
            messagebox.showerror("Errore API Key", error_msg)
        except Exception:
            pass
        sys.exit(1)

    # 3. Inizializza i componenti
    ai_client = AIClient(api_key)
    
    # Crea il worker usando la nuova classe semplificata
    worker = TranscriptionWorker(ai_client) 

    # 4. Avvia il worker in un thread in background
    worker_thread = threading.Thread(target=worker.run, daemon=True)
    worker_thread.start()

    # 5. Avvia l'interfaccia grafica (GUI)
    print("🚀 Avvio dell'Assistente Lezione...")
    launch_gui(ai_client)