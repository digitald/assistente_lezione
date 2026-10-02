# Assistente Lezione 2.0.0

Applicazione web locale per registrare o importare una lezione in italiano, revisionare la trascrizione e creare appunti formattati. Python acquisisce l'audio e conserva i dati sul PC; il browser è l'interfaccia. OpenAI è il motore iniziale, faster-whisper su CPU o NVIDIA è l'alternativa locale.

## Installazione e avvio

Windows con **Python 3.12 a 64 bit**. Clona il repository oppure estrai il pacchetto del programma, poi:

1. Apri `installa_windows.cmd`: crea `.venv`, installa le dipendenze fissate e prepara `config.py` senza sovrascriverlo.
2. Configura `OPENAI_API_KEY` in `config.py` oppure nell'ambiente. La trascrizione locale non richiede una chiave; gli appunti AI la richiedono.
3. Apri `avvia_lezione.cmd`: il pannello è su [127.0.0.1:8765](http://127.0.0.1:8765).
4. Per una prova senza API e microfono usa `avvia_prova.cmd`, con archivio separato e porta 8766.

La [guida Windows](docs/INSTALLAZIONE_ALTRO_PC.md) descrive installazione, trasferimento dei dati, configurazione GPU e diagnosi. Python e librerie vengono installati sul PC e non sono distribuiti nel repository.

## Uso quotidiano

- **Registra subito:** avvia il microfono predefinito e crea una lezione con data e ora, anche senza profilo. Compila **Dati della lezione** durante o dopo la registrazione e salva. Il motore è OpenAI; in demo è simulato.
- **Nuova lezione:** configura il profilo docente con corso, insegnamento, anno e sezione, scegli la classe e il titolo. In **Opzioni di trascrizione** puoi cambiare motore e modello prima di registrare.
- **Importa audio:** scegli un file, conferma titolo e classe, poi premi **Crea e importa audio**. Sono ammessi WAV, MP3, M4A, MP4, WebM, OGG, FLAC, MPEG e MPGA; file e richiesta devono rientrare in **512 MiB**. Per Google Recorder occorre esportare il file sul PC: non è un collegamento all'account.
- **Pausa / Riprendi** controllano l'acquisizione. **Ferma e trascrivi** chiude l'audio e avvia il riconoscimento. È consentita una sola registrazione attiva.
- Revisiona la **Trascrizione**, salva e premi **Genera appunti**. Gli appunti hanno vista **Lettura**, editor **Modifica**, titoli, elenchi, enfasi e citazioni. `Ctrl+S` salva l'editor attivo o il modulo dei dati della lezione.
- **Esporta**, accanto alle schede, raccoglie Trascrizione TXT, Appunti TXT, Appunti Markdown, Appunti Stampa/PDF e audio originale. Le uscite usano i contenuti salvati. PDF usa la stampa del browser e riguarda gli appunti.

Chiudere la scheda del browser **non ferma la registrazione**. Usa Ferma e lascia il server aperto durante le lavorazioni. Dopo una ricarica, il banner permette di ritrovare la sessione attiva. I dati salvati restano nel database; le bozze dei moduli profilo/nuova lezione dipendono dal browser e non sostituiscono il salvataggio.

## Archivio e spazio su disco

La navigazione distingue **Lezioni**, **Archiviate** e **Cestino**. Archiviare o spostare nel cestino conserva i file; solo **Elimina definitivamente**, con conferma, rimuove i dati e libera spazio. Per modificare una lezione archiviata occorre ripristinarla.

| Percorso locale, escluso da Git | Contenuto |
| --- | --- |
| `config.py`, `.env*` | Configurazione privata; l'app legge config.py e variabili d'ambiente, non carica automaticamente .env. |
| `data/archive.sqlite3` | Profilo, lezioni, stati, testi e progresso dei segmenti. |
| `data/<id>/` | Audio originale, normalizzato, segmenti, testi e precedenti appunti. |
| `data/models/` | Modelli locali scaricati al primo uso. |
| `data/validation/` | Campioni e risultati delle prove locali. |
| `web-demo-data/`, `demo_data/` | Archivi dimostrativi separati. |
| `transcripts/`, `notes/` | Archivio della precedente interfaccia desktop. |
| `.venv/`, `.runtime/` | Dipendenze e, dove presente, interprete Python locale. |
| `test-artifacts/`, `dist/` | Anteprime dei collaudi e ZIP generati. |

Per un backup coerente chiudi i server e copia **tutta `data`**, non il solo database. Per spostare il progetto segui la guida: gli ambienti Python vanno ricreati e le vecchie cartelle importate non vanno sovrapposte all'archivio già migrato.

Originale, audio normalizzato e segmenti occupano spazio intenzionalmente: consentono ascolto e recupero. Con registrazione mono PCM16 a 16 kHz, tre copie equivalgono a circa 0,69 GB per due ore o 1,04 GB per tre ore; frequenze maggiori possono aumentare questi valori. Non cancellare singoli file di una lezione per liberare spazio.

## Motori, recupero e limiti

OpenAI usa `gpt-transcribe` per le nuove lezioni; sono presenti anche selezioni di compatibilità. Il modello locale può essere Base, Small, Medium, Large v3 Turbo o Large v3. Hardware e precisione si impostano in `config.py`; riavvia il server dopo una modifica. Per CUDA e prove di velocità consulta la guida Windows.

La trascrizione parte dopo l'arresto, suddivide l'audio in parti fino a due minuti e salva ogni parte completata. **Riprova trascrizione** riprende quelle incomplete. Dopo un arresto improvviso la sessione viene indicata come interrotta; il recupero di un WAV danneggiato non è garantito. Una riprova dopo un errore remoto può comportare un nuovo costo.

La trascrizione locale non invia l'audio a OpenAI; gli appunti inviano comunque il testo. Sono un documento unico con massimo 4.000 token di uscita: su lezioni lunghe non garantiscono copertura dettagliata di ogni argomento. Risposte vuote o troncate non sostituiscono gli appunti precedenti. Costi e disponibilità dei servizi dipendono dall'account: consultare il fornitore prima di elaborazioni estese.

Il pannello ascolta solo su `127.0.0.1`, serve esclusivamente gli asset web e non espone la chiave. È pensato per un docente e un archivio locale: non implementa account multipli, sincronizzazione, traduzione, identificazione dei parlanti o trascrizione live. La ricerca riguarda i metadati. La vecchia interfaccia Tkinter rimane accessibile con `avvia_desktop.cmd` per compatibilità.

## Documentazione e sviluppo

- [Installazione su un altro PC e NVIDIA](docs/INSTALLAZIONE_ALTRO_PC.md)
- [Architettura, lavoro realizzato, verifiche e limiti](docs/STATO_PROGETTO.md)
- [Controllo della qualità delle trascrizioni](docs/VERIFICA_TRASCRIZIONI.md)
- [Note di versione](CHANGELOG.md)

Controlli senza chiamate cloud o microfono reale, con il Python di `.venv`:

```text
python -X utf8 -m unittest discover -s tests -v
python -m pip check
python verifica_ambiente.py
```

I collaudi browser richiedono Node, Playwright e Edge: `python tests/check_all_browser.py`. Il comando avvia un archivio temporaneo nuovo per ciascun test. `PLAYWRIGHT_MODULE` può indicare un'installazione già disponibile. Anteprime rigenerabili in `test-artifacts` non entrano in Git.

La versione è definita in `version.py`, esposta dal pannello, dall'API e da `python main.py --version`. `python prepara_trasferimento.py` produce `dist/AssistenteLezione-2.0.0.zip`: sorgenti, documentazione, test e istruzioni delle dipendenze, senza librerie installate, dati personali, chiavi, modelli, screenshot o log. Il comando non sovrascrive pacchetti precedenti. Il tag Git è `v2.0.0`.
