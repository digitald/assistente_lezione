# Installare e trasferire Assistente Lezione su Windows

Versione 2.0.0 — 2 ottobre 2026. OpenAI resta la scelta iniziale per le nuove lezioni: Il motore locale è un'alternativa selezionabile, con configurazione CPU o NVIDIA.

## 1. Installazione del programma

1. Copia `dist/AssistenteLezione-2.0.0.zip` sul nuovo PC ed estrailo in una cartella locale, per esempio `C:\Applicazioni\AssistenteLezione`. Non eseguire il programma dentro lo ZIP.
2. Installa **Python 3.12 a 64 bit**, con il launcher `py`, dal [sito ufficiale Python](https://www.python.org/downloads/windows/). Le dipendenze fissate nel progetto sono state collaudate con Python 3.12.10; la procedura verifica la famiglia 3.12 e l'architettura a 64 bit.
3. Apri `installa_windows.cmd`. Crea l'ambiente `.venv`, scarica le dipendenze fissate in `requirements-lock.txt`, ne controlla la compatibilità e crea `config.py` dal template solo se assente. Serve Internet per questo passaggio. Se compare un errore, l'installazione si ferma lasciandolo visibile.
4. Apri `avvia_prova.cmd` per controllare l'interfaccia senza chiamate AI o microfono. La demo usa un archivio separato sulla porta 8766.
5. Per OpenAI, inserisci la chiave in `config.py` oppure nella variabile d'ambiente `OPENAI_API_KEY`. Non includere la chiave nei pacchetti del programma. Chiudi e riapri il server dopo un cambio di configurazione.
6. Apri `avvia_lezione.cmd`, quindi il pannello su `http://127.0.0.1:8765`. Configura il profilo o trasferisci l'archivio come descritto sotto.

Lo ZIP include programma, interfaccia, test e documentazione. Esclude chiavi, lezioni, modelli scaricati, log e ambienti Python. `.venv` e `.runtime` del vecchio PC non sono portabili: vanno ricreati attraverso l'installazione. Se esiste già un ambiente incompatibile, usa una nuova cartella di installazione.

Per ricreare un pacchetto dopo aggiornamenti, dalla cartella del progetto:

```powershell
.\.venv\Scripts\python.exe prepara_trasferimento.py --output dist/AssistenteLezione-aggiornato.zip
```

Il comando rifiuta di sovrascrivere uno ZIP esistente. L'installazione completa su un secondo Windows non è ancora stata eseguita: il pacchetto e le dipendenze sono verificati sul PC attuale.

## 2. Trasferire profilo, lezioni, audio e appunti

1. Termina registrazioni e lavorazioni, poi chiudi i server di entrambi i PC. Chiudere la sola scheda del browser non arresta il server.
2. Conserva una copia di sicurezza della cartella **`data` intera** del vecchio PC. Contiene `archive.sqlite3` (anche il profilo docente) e le cartelle delle lezioni con audio e documenti. Copiare soltanto il database non trasferisce gli audio.
3. Sul nuovo PC, prima del primo utilizzo reale, copia `data` nella cartella del programma. Se esiste già un archivio usato sul nuovo PC, conservane una copia separata: non sovrapporre due archivi. La fusione automatica non è implementata.
4. `data/models` può essere trasferita per evitare nuovi download oppure omessa e riscaricata al primo utilizzo locale. Non contiene lezioni, ma può occupare diversi GB.
5. Avvia il programma nuovo. Verifica nome del docente, classi, numero di lezioni, apertura di una trascrizione e di un appunto, riproduzione di un audio. Ricarica il browser e ripeti l'apertura.

Le cartelle storiche `transcripts` e `notes` vengono importate automaticamente. Se quelle lezioni sono già in `data`, **non copiarle nuovamente nelle cartelle di importazione attive**: cambiando il percorso assoluto, la vecchia identificazione dell'importazione potrebbe produrre duplicati. Conservale eventualmente in un backup separato. Il nuovo `config.py` deve usare i percorsi relativi alla nuova installazione, come nel template.

Le bozze non salvate dei moduli vivono nel browser e non viaggiano con `data`. Salva il profilo e gli editor prima del trasferimento. Questa procedura è una copia a server spento, non un backup automatico durante l'uso. I due PC hanno archivi indipendenti, senza sincronizzazione.

## 3. Trascrizione locale su CPU

La configurazione iniziale è CPU INT8. Funziona senza chiave API; il primo download del modello richiede Internet. Gli appunti AI richiedono comunque OpenAI e inviano al servizio il testo.

In `config.py` puoi aggiungere o aggiornare:

```python
LOCAL_DEVICE = "cpu"
LOCAL_COMPUTE_TYPE = "int8"
LOCAL_CPU_THREADS = 8
LOCAL_DEVICE_INDEX = 0
```

Otto thread sono un punto iniziale di prova per il futuro Intel a 12 core, non una misura ottimale già verificata. Confronta 8 e 12 sullo stesso audio prima di aumentare; più thread non garantiscono più velocità. Sul PC attuale il valore automatico è 6.

Nel modulo Nuova lezione, apri **Opzioni di trascrizione → Locale** e scegli Base, Small, Medium, Large v3 Turbo o Large v3. La selezione del modello è salvata nella lezione; cambiare configurazione hardware richiede il riavvio del server. La prima trascrizione con un modello mancante ne avvia il download.

## 4. NVIDIA da 8 o 12 GB

Il progetto ora passa esplicitamente dispositivo, precisione, indice GPU e thread a faster-whisper. Per le versioni delle dipendenze fissate nel progetto, prepara:

- driver NVIDIA compatibili con la GPU;
- **CUDA 12 con cuBLAS**;
- **cuDNN 9 per CUDA 12**, con le DLL raggiungibili dal `PATH` del processo;
- runtime Microsoft Visual C++ richiesto da CTranslate2 su Windows.

Riferimenti: [requisiti di faster-whisper](https://github.com/SYSTRAN/faster-whisper#gpu), [installer cuDNN per Windows](https://docs.nvidia.com/deeplearning/cudnn/installation/latest/windows.html), [installazione CTranslate2](https://opennmt.net/CTranslate2/installation.html). Alcune pagine generiche riportano ancora cuDNN 8: il [passaggio a cuDNN 9 è documentato dal rilascio CTranslate2 4.5](https://github.com/OpenNMT/CTranslate2/releases/tag/v4.5.0). Non mescolare quelle istruzioni con le dipendenze attuali. L'installer del progetto non installa driver o librerie NVIDIA; PyTorch non è richiesto per questo motore.

Configurazione iniziale proposta per il nuovo PC:

```python
LOCAL_DEVICE = "cuda"
LOCAL_COMPUTE_TYPE = "float16"
LOCAL_CPU_THREADS = 8
LOCAL_DEVICE_INDEX = 0
```

Per 8 GB, partire da **Large v3 Turbo** e provarlo su alcuni minuti di lezione. Se la memoria non basta, confrontare `int8_float16`, che riduce l'uso di memoria dei pesi, oppure un modello più piccolo. Per 12 GB, provare Turbo e confrontarlo con **Large v3** sul medesimo file. Sono punti di partenza da collaudare: la memoria libera, la GPU esatta, il modello e gli altri programmi influenzano il risultato. Non sono promesse di velocità, compatibilità o qualità. Il vantaggio rispetto a OpenAI va misurato sul lessico delle proprie lezioni.

Il programma segnala esplicitamente dispositivo o precisione non disponibili: non passa silenziosamente alla CPU. Per tornare alla CPU, impostare `cpu` e `int8`, quindi riavviare. Non basta che la scheda compaia nella diagnosi: una trascrizione reale deve riuscire per confermare anche le DLL e l'inferenza.

## 5. Verifica ripetibile sul nuovo PC

Apri PowerShell nella cartella del programma. Diagnosi senza caricamento del modello:

```powershell
.\.venv\Scripts\python.exe -X utf8 verifica_locale.py --device cuda --compute-type float16
```

Prova completa, con un file breve di cui conosci il contenuto:

```powershell
.\.venv\Scripts\python.exe -X utf8 verifica_locale.py --device cuda --compute-type float16 --model large-v3-turbo --audio "C:\Audio\campione.m4a" --download
```

Per confrontare Large v3, ripeti cambiando `--model large-v3`. Per CPU usa `--device cpu --compute-type int8 --model small`. `--download` autorizza il download del modello mancante; senza questa opzione la verifica usa solo modelli già sul disco. Il file audio viene normalizzato attraverso lo stesso componente dell'applicazione.

Risultati separati in `data/validation`: TXT e JSON con durata dell'audio, tempo di caricamento, normalizzazione, trascrizione e rapporto tempo di trascrizione/durata audio. Un rapporto inferiore a 1 indica elaborazione più veloce della durata del campione, escludendo caricamento e normalizzazione. Nessuna richiesta cloud e nessuna modifica alle lezioni esistenti. Il campionamento a blocchi fissi del comando non riproduce esattamente il taglio vicino ai silenzi dell'applicazione su audio lunghi.

## 6. Microfono e collaudo d'uso

Sul nuovo PC collega il microfono, abilita in Windows l'accesso al microfono per le applicazioni desktop, poi riavvia il programma per aggiornare l'elenco dei dispositivi. Prima di una lezione lunga registra un minuto nella posizione effettiva d'uso, controlla il livello, riascolta il WAV e trascrivilo. Verifica parole tecniche, nomi e numeri. La scelta del microfono dipende soprattutto da distanza dalla voce e movimento in aula; non è stato ancora selezionato o collaudato un modello specifico.

Per una registrazione già disponibile, usa **Importa audio**, conferma titolo e classe e attendi la trascrizione. Sono supportati WAV, MP3, M4A, MP4, WebM, OGG e FLAC entro il limite di 512 MiB. È stato verificato un M4A/AAC sintetico; l'esportazione dallo specifico registratore Google andrà provata con un suo file reale.

## Problemi frequenti

| Sintomo | Controllo |
| --- | --- |
| `py` o Python 3.12 non trovato | Installa Python 3.12 x64 con il launcher e riapri l'installer. |
| DLL NVIDIA mancante | Controlla versioni CUDA/cuDNN e PATH, riapri il terminale; esegui la prova con audio. |
| Memoria GPU esaurita | Chiudi programmi che usano la GPU; prova Turbo, `int8_float16` o un modello minore. |
| Si apre una versione precedente | Ferma il server già in ascolto prima di avviare quello aggiornato; ricarica il browser. |
| Profilo assente sul nuovo PC | Verifica che sia stato copiato `data/archive.sqlite3` nell'installazione avviata. |
| Nessun microfono disponibile | Verifica collegamento, autorizzazioni Windows e dispositivo selezionato; l'importazione audio non richiede microfono. |

Per il risultato dei controlli già eseguiti, leggere [Verifica trascrizioni](VERIFICA_TRASCRIZIONI.md) e [Stato progetto](STATO_PROGETTO.md).
