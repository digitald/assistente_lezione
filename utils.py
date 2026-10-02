# utils.py (versione finale per Assistente Lezione)

from pathlib import Path

import config
import shared_state
from ai_client import AIClient

def generate_and_save_notes(session_id: str, ai_client: AIClient) -> bool:
    """
    Genera gli appunti in italiano leggendo la trascrizione da file.
    NON traduce più in inglese.
    """
    transcript_filepath = Path(config.TRANSCRIPTS_DIR) / f"trascrizione_{session_id}.txt"

    if not transcript_filepath.exists():
        print(f"❌ File trascrizione non trovato per generare gli appunti: {transcript_filepath}")
        return False

    with open(transcript_filepath, "r", encoding="utf-8") as f:
        transcript_text = f.read()
    if not transcript_text.strip():
        return False

    print(f"⏳ Elaborazione appunti per {session_id} da file...")
    italian_notes = ai_client.summarize_transcript(transcript_text)

    if italian_notes:
        notes_filepath = Path(config.NOTES_DIR) / f"appunti_{session_id}.txt"
        notes_filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(notes_filepath, "w", encoding="utf-8") as f:
            f.write(italian_notes)
        print(f"✅ Appunti salvati in {notes_filepath}")
        return True # L'operazione è conclusa con successo
    else:
        print(f"❌ Errore durante l'elaborazione degli appunti per {session_id}.")
        return False

def save_transcript_to_file(session_id: str) -> str | None:
    """
    Formatta la trascrizione (solo italiano) e la salva in un file permanente.
    """
    session_data = shared_state.session_transcripts.get(session_id)
    if session_data is None:
        return None

    # CORREZIONE: Usa il nuovo formato con un solo campo "text"
    lines = [f"[{r.get('timestamp', '')}] {r.get('text', '')}" for r in session_data["transcripts"]]
    transcript_text = "\n".join(lines)
    
    filepath = Path(config.TRANSCRIPTS_DIR) / f"trascrizione_{session_id}.txt"
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        temporary = filepath.with_suffix(".txt.tmp")
        with open(temporary, "w", encoding="utf-8") as f:
            f.write(transcript_text)
        temporary.replace(filepath)
        print(f"✅ Trascrizione permanente salvata in: {filepath}")
        return str(filepath)
    except Exception as e:
        print(f"❌ Errore nel salvataggio della trascrizione: {e}")
        return None
