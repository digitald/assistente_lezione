# main.py (Versione 2, più semplice)

import os
import sys
from tkinter import messagebox

import config
from ai_client import AIClient
from gui import launch_gui

if __name__ == "__main__":
    # Crea le cartelle necessarie
    os.makedirs(config.NOTES_DIR, exist_ok=True)
    os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)

    # Controlla la API Key (necessaria per gli appunti e la modalità API)
    api_key = os.getenv("OPENAI_API_KEY", config.OPENAI_API_KEY)
    if not api_key or api_key == "sk-...":
        error_msg = "API key di OpenAI non trovata o non configurata in config.py"
        print(f"❌ {error_msg}")
        try:
            messagebox.showerror("Errore API Key", error_msg)
        except Exception: pass
        sys.exit(1)

    # Inizializza solo il client AI, che serve sempre per gli appunti
    ai_client_for_notes = AIClient(api_key)

    # Avvia l'interfaccia grafica. Sarà lei a gestire il worker.
    print("🚀 Avvio dell'Assistente Lezione...")
    launch_gui(ai_client_for_notes)