# Assistente Lezione v1.1

Un'applicazione desktop per Windows, macOS e Linux che assiste docenti e studenti registrando, trascrivendo e riassumendo lezioni in italiano. Il programma utilizza le API di OpenAI per fornire trascrizioni accurate e generare appunti strutturati.

## Caratteristiche Principali

-   **Registrazione Semplificata**: Avvia, metti in pausa, riprendi e ferma la registrazione della lezione con un'interfaccia grafica intuitiva.
-   **Trascrizione in Tempo Reale**: Cattura l'audio dal microfono e lo trascrive in testo italiano utilizzando il modello Whisper di OpenAI.
-   **Gestione Sessioni**: Assegna a ogni lezione un ID basato su docente, materia e data per una facile archiviazione e consultazione.
-   **Generazione di Appunti con AI**: A fine lezione, è possibile elaborare l'intera trascrizione con GPT-4o per creare appunti strutturati, con titoli, elenchi e concetti chiave evidenziati.
-   **Archivio Lezioni**: Visualizza una lista di tutte le lezioni passate, con icone che indicano lo stato (Trascrizione salvata 📜, Appunti generati 📝).
-   **Controllo Completo**: Tutte le funzioni sono accessibili da un unico pannello di controllo desktop.

## Struttura del Progetto

Il codice è organizzato in moduli per facilitare la manutenzione.
/Assistente_Lezione/
├── notes/                # Cartella per gli appunti salvati (creata automaticamente)
├── transcripts/          # Cartella per le trascrizioni salvate (creata automaticamente)
|
├── main.py               # Script principale per avviare l'applicazione
├── gui.py                # Interfaccia grafica (Tkinter)
├── ai_client.py          # Gestione delle chiamate alle API di OpenAI
├── audio_worker.py       # Logica per la cattura e l'elaborazione dell'audio
├── utils.py              # Funzioni di supporto (salvataggio file, ecc.)
├── config.py             # File di configurazione (NON CARICARE SU GITHUB)
├── shared_state.py       # Stato condiviso tra i moduli
└── requirements.txt      # Lista delle dipendenze Python


## Installazione

#### Prerequisiti
-   Python 3.8 o superiore.
-   Un account OpenAI con una API Key valida.
-   Git installato sul proprio computer.

#### Procedura di Installazione
1.  **Clona il Repository**:
    ```bash
    git clone <URL_DEL_TUO_REPOSITORY>
    cd Assistente_Lezione
    ```

2.  **Installa le Dipendenze**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configura la API Key**:
    -   Crea una copia del file `config.template.py` (se lo hai creato) e rinominala in `config.py`.
    -   Apri `config.py` e inserisci la tua API Key di OpenAI nella variabile `OPENAI_API_KEY`.

## Utilizzo

Per avviare l'applicazione, esegui lo script principale dal terminale:
```bash
python main.py