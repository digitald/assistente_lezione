"""Contenuti simulati per collaudare il flusso senza servizi esterni."""

DEMO_SEGMENTS = (
    "PROVA SIMULATA. Oggi studiamo il ciclo dell'acqua: evaporazione, condensazione e precipitazione.",
    "Il Sole riscalda l'acqua di mari e laghi. L'acqua evapora e sale nell'atmosfera sotto forma di vapore.",
    "Il vapore si raffredda e condensa in goccioline, formando le nuvole. Le precipitazioni riportano l'acqua al suolo.",
    "Una parte dell'acqua si infiltra nel terreno, mentre un'altra scorre nei fiumi e ritorna al mare.",
)


class DemoAIClient:
    def summarize_transcript(self, transcript_text):
        if not transcript_text.strip():
            return ""
        # La demo riporta soltanto i segmenti effettivamente acquisiti.
        lines = [line.partition("] ")[2] or line for line in transcript_text.splitlines() if line.strip()]
        return "# Appunti di prova simulati\n\n> Nessuna elaborazione AI eseguita.\n\n## Contenuti della lezione\n\n" + "\n".join(f"- {line}" for line in lines) + "\n"
