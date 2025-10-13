# ai_client.py (versione semplificata per Assistente Lezione)

import openai
from pathlib import Path

class AIClient:
    def __init__(self, api_key: str):
        openai.api_key = api_key
        self.client = openai

    def transcribe(self, file_object) -> str:
        """
        Trascrive un file audio, specificando che è in italiano.
        """
        try:
            prompt_migliorato = (
                "Stai trascrivendo una lezione universitaria in italiano, restitusci una stringa vuota in caso di volume troppo basso o di contenuto inintellegibile"
            )

            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=file_object,
                prompt=prompt_migliorato,
                language="it" # <-- AGGIUNGI QUESTA RIGA
            )
            return transcript.text.strip()
        except Exception as e:
            print(f"❌ Errore trascrizione: {e}")
            return ""

    def summarize_transcript(self, transcript_text: str) -> str:
        """
        Elabora una trascrizione completa per creare appunti strutturati in italiano.
        """
        if not transcript_text.strip():
            return ""
            
        try:
            prompt = f"""
Sei un assistente universitario specializzato nel creare appunti chiari e ben organizzati.
Trasforma la seguente trascrizione di una lezione in italiano in un riassunto strutturato. 
Usa titoli, elenchi puntati e grassetto per evidenziare i concetti chiave. 
L'output deve essere in italiano.

Trascrizione:
---
{transcript_text}
---

Appunti Strutturati:
"""
            
            resp = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Sei un assistente specializzato nella creazione di appunti universitari in italiano."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
                temperature=0.7
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"❌ Errore nell'elaborazione della trascrizione: {e}")
            return ""