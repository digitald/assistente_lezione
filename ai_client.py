# ai_client.py (versione semplificata per Assistente Lezione)

import openai
from pathlib import Path

class AIClient:
    def __init__(self, api_key: str):
        openai.api_key = api_key
        self.client = openai

    def transcribe(self, file_object) -> str:
        """
        Trascrive un file audio in testo italiano.
        """
        try:
            prompt_migliorato = (
                "Sei un sistema di trascrizione per una lezione universitaria in italiano. Il tuo obiettivo è produrre un testo pulito, accurato e ben formattato. Segui queste regole in modo tassativo:\n"
                "1. Trascrivi solo le parole. Ignora completamente pause, silenzi, esitazioni (come 'uhm', 'ehm'), ripetizioni, parole smozzicate, rumori di fondo, colpi di tosse e qualsiasi altro suono non verbale.\n"
                "2. Applica la punteggiatura corretta. Usa virgole, punti, maiuscole e punti interrogativi in modo appropriato per rendere il testo fluente e grammaticalmente corretto.\n"
                "3. Crea paragrafi. Suddividi il testo in paragrafi distinti quando percepisci un cambio di argomento o una pausa significativa nel discorso del relatore.\n"
                "4. Non descrivere i suoni. L'output non deve mai contenere etichette tra parentesi come [risata], [rumore] o [silenzio].\n"
                "Il risultato finale deve essere esclusivamente il testo della lezione, pulito e pronto per la lettura."
            )

            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=file_object,
                prompt=prompt_migliorato
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