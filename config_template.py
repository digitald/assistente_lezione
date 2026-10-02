# Copia questo template in config.py, senza sovrascrivere una chiave già inserita.

# Istruzioni:
# 1. Inserisci la tua API key di OpenAI al posto di "sk-...".
# 2. Rinomina questo file in "config.py".

OPENAI_API_KEY = "sk-..."

from pathlib import Path
PROJECT_DIR = Path(__file__).resolve().parent

# Nomi delle directory per i file salvati (puoi lasciarli così)
NOTES_DIR = str(PROJECT_DIR / "notes")
TRANSCRIPTS_DIR = str(PROJECT_DIR / "transcripts")

# Trascrizione locale. Dopo le modifiche riavvia il server.
LOCAL_DEVICE = "cpu"  # "cuda" solo con una GPU NVIDIA configurata.
LOCAL_COMPUTE_TYPE = ""  # Vuoto: int8 su CPU, float16 su CUDA.
LOCAL_CPU_THREADS = max(1, min(8, (__import__('os').cpu_count() or 4) - 2))
LOCAL_DEVICE_INDEX = 0
