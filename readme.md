# Assistente Lezione v2.2

Un'applicazione desktop per Windows, macOS e Linux che assiste docenti e studenti registrando, trascrivendo e riassumendo lezioni in italiano. Questa versione introduce la possibilità di scegliere tra l'elaborazione online tramite API e l'esecuzione in locale su CPU o GPU.

## Caratteristiche Principali

-   **Registrazione Flessibile**: Avvia, metti in **pausa**, riprendi e ferma la registrazione della lezione con un'interfaccia grafica intuitiva.
-   **Motore di Trascrizione Selezionabile**:
    -   **Modalità API**: Sfrutta la massima accuratezza del modello Whisper di OpenAI.
    -   **Modalità Locale (GPU/CPU)**: Esegue la trascrizione direttamente sul computer (usando `faster-whisper`) per la massima privacy e per azzerare i costi, con performance elevate su hardware compatibile.
-   **Gestione Sessioni**: Assegna a ogni lezione un ID descrittivo (Docente, Materia, Data) per una facile archiviazione e consultazione.
-   **Generazione di Appunti con AI**: A fine lezione, elabora la trascrizione con GPT-4o per creare appunti strutturati in italiano.
-   **Archivio Lezioni**: Visualizza una lista di tutte le lezioni passate, con icone di stato (Trascrizione salvata 📜, Appunti generati 📝) per vedere a colpo d'occhio cosa è stato fatto.
-   **Pannello di Controllo Unificato**: Tutta la gestione avviene da un'unica finestra desktop.

## Struttura del Progetto

/Assistente_Lezione/
├── notes/
├── transcripts/
|
├── main.py               # Script principale per avviare l'applicazione
├── gui.py                # Interfaccia grafica (Tkinter)
├── ai_client.py          # Gestione delle chiamate alle API di OpenAI
├── audio_worker.py       # Logica per la cattura e l'elaborazione dell'audio
├── transcribers.py       # "Motori" di trascrizione (API e Locale)
├── utils.py              # Funzioni di supporto (salvataggio file, ecc.)
├── config.py             # File di configurazione (NON CARICATO SU GITHUB)
├── config.template.py    # Modello per il file di configurazione
├── shared_state.py       # Stato condiviso tra i moduli
└── requirements.txt      # Lista delle dipendenze Python


## Installazione

#### Prerequisiti
-   Python 3.8 o superiore.
-   Git installato sul proprio computer.
-   Una chiave API di OpenAI (necessaria per la modalità API e per la generazione degli appunti).
-   (Opzionale, per la modalità GPU) Una scheda video NVIDIA con driver CUDA e PyTorch installato correttamente.

#### Procedura
1.  **Clona il Repository**:
    ```bash
    git clone <URL_DEL_TUO_REPOSITORY>
    cd Assistente_Lezione
    ```

2.  **Installa le Dipendenze**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configura l'Applicazione**:
    -   Crea una copia del file `config.template.py` e rinominala in `config.py`.
    -   Apri `config.py` e inserisci la tua API Key di OpenAI.
    -   Nello stesso file, puoi impostare la modalità di esecuzione predefinita (`EXECUTION_MODE`).

## Utilizzo

Per avviare l'applicazione, esegui lo script principale dal terminale:
```bash
python main.py

    Scelta della Modalità: All'avvio, seleziona dall'interfaccia se vuoi usare le API online, la GPU o la CPU.

    Dettagli Lezione: Inserisci il nome del docente e della materia.

    Avvio: Clicca su "▶ Avvia" per iniziare la registrazione. L'etichetta di stato lampeggerà in rosso per indicare che la registrazione è attiva.

    Pausa/Stop: Usa i pulsanti "⏸ Pausa" per interrompere temporaneamente la trascrizione e "⏹ Ferma" per terminare la sessione e salvare il file della trascrizione.

    Gestione Archivio: A fine lezione, la nuova sessione apparirà nella lista. Selezionala per generare gli appunti o per visualizzare i file di testo.