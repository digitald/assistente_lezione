"""Messaggi condivisi dalle interfacce web e desktop."""
import sounddevice as sd


def error_message(exc):
    status = getattr(exc, "status_code", None)
    if status == 401:
        return "Chiave API non valida: controlla config.py."
    if status == 429:
        return "Limite API o credito esaurito: controlla il tuo account OpenAI."
    if status in (403, 404):
        return "Accesso al modello AI non disponibile per questo account."
    if isinstance(exc, sd.PortAudioError):
        return "Impossibile acquisire il microfono: controlla dispositivo e permessi audio di Windows."
    if isinstance(exc, OSError):
        return "Impossibile scrivere i file: controlla cartella e spazio disponibile."
    return f"Operazione non riuscita ({type(exc).__name__}). Controlla connessione e accesso API."
