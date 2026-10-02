# Stato tecnico — Assistente Lezione 2.0.0

Rilascio del 2 ottobre 2026. Risultato corrente del lavoro: [README](../readme.md) per l'uso, [guida Windows](INSTALLAZIONE_ALTRO_PC.md) per installazione e trasferimento, [changelog](../CHANGELOG.md) per le novità. La proposta iniziale rimane nella cronologia Git.

## Struttura e responsabilità

| Componente | Responsabilità |
| --- | --- |
| main.py, web_app.py | Avvio, Flask/Waitress locale, API, token dei comandi, upload e download. Il desktop viene importato solo se richiesto. |
| lesson_service.py | SQLite, profilo, lezioni, metadati, coda, registrazione, trascrizione e appunti. |
| audio_capture.py | Scrittura separata dal callback del microfono, coda limitata e chiusura dopo drenaggio. |
| audio_processing.py | PyAV e normalizzazione mono PCM16 a 16 kHz condivisa con la diagnosi locale. |
| local_runtime.py | Modelli consentiti, configurazione CPU/CUDA, controllo della precisione e caricamento. |
| transcript_tools.py | Paragrafi conservativi e riferimenti temporali senza correzioni delle parole. |
| ai_client.py | Richieste AI, prompt degli appunti, rifiuto di uscite vuote/troncate. |
| app_errors.py | Messaggi condivisi senza dipendenza dal worker desktop o dalla configurazione privata. |
| web/ | HTML/CSS e script di archivio, profilo, editor, appunti, dialoghi e avvio rapido. |
| version.py | Unica versione per API, interfacce, riga di comando e pacchetto. |
| gui.py, audio_worker.py, shared_state.py, utils.py | Interfaccia Tkinter precedente, mantenuta per compatibilità con test propri. |
| tests/, verifica_*.py | Test isolati, collaudi browser, diagnosi hardware e prove audio. |
| installa_windows.cmd, prepara_trasferimento.py | Installazione riproducibile e ZIP dei soli file distribuibili. |

## Funzioni e correzioni realizzate

- Interfaccia chiara con contrasto, navigazione Lezioni/Archiviate/Cestino, ricerca nei metadati, documento centrale, dialoghi con gestione del focus e adattamento mobile.
- Profilo e classi persistenti in SQLite; bozze nel browser senza bloccare l'app quando lo storage non è disponibile.
- Risolto il blocco dei pulsanti causato dal template Flask vecchio insieme a script aggiornati: template ricaricabile e test di regressione. Rinnovo del token scaduto con una sola ripetizione del comando esplicitamente rifiutato prima dell'esecuzione; nessuna ripetizione automatica dopo errori di rete.
- Registrazione su disco, pausa/ripresa, livello, importazione e riproduzione. Avvisi di acquisizione conservati nella lezione.
- Avvio rapido senza dati preliminari: creazione e avvio sotto lo stesso lock, una sola sessione, errore microfono recuperabile. Metadati modificabili durante la registrazione senza cambiare stato, audio, testi o profilo.
- Trascrizione differita a segmenti, salvataggio progressivo e recupero delle parti incomplete. Modelli locali su CPU/NVIDIA senza ripiego silenzioso dalla GPU alla CPU.
- Trascrizione modificabile e appunti Markdown con lettura/editor. Il renderer crea solo elementi DOM consentiti: HTML e link non diventano codice. PDF tramite stampa del browser.
- Menu Esporta unico: TXT trascrizione, TXT/MD/PDF appunti e audio. Modifiche pendenti da salvare prima di esportare il documento interessato.
- Archivio e cestino reversibili, eliminazione definitiva confermata, importazione legacy e copia dei precedenti appunti prima della rigenerazione.
- Corretto anche il prototipo desktop: coda ordinata, risposte attribuite alla sessione originale, attesa del tratto finale e aggiornamenti GUI nel thread principale.

## Dati e prestazioni

SQLite conserva payload completo e riepilogo separato per ogni lezione. La migrazione popola automaticamente i riepiloghi dei vecchi database. Ogni modifica aggiorna una revisione: il browser richiede il dettaglio solo quando cambia. Una risposta relativa alla selezione precedente non sostituisce la lezione corrente.

Polling: 1 s durante la registrazione, 3 s durante altre lavorazioni, 5 s a riposo e 15 s con scheda nascosta. Richieste non sovrapposte e timeout delle letture. Prova con 40 lezioni da circa 360.000 caratteri, media di 15 letture: 25,65 ms per payload completi e 10,47 ms per riepiloghi. È una misura del servizio, non un rapporto equivalente di riduzione del traffico HTTP.

Il writer usa 128 blocchi. Con 1.024 campioni mono float32 per blocco, contiene fino a circa 512 KiB di campioni oltre all'overhead. La memoria non cresce con l'intera durata. In caso di disco lento segnala errore e drena i blocchi già accettati. La scrittura periodica non garantisce recupero dopo un'interruzione di alimentazione.

Whisper mantiene un solo modello in memoria. Dispositivo, precisione, thread e indice GPU sono configurabili; le variabili LESSON_LOCAL_* prevalgono su config.py. Default CPU INT8 e massimo 8 thread, ridotto sui processori con meno thread. Il controllo di compatibilità non sostituisce una prova di inferenza NVIDIA.

App e diagnosi passano campioni normalizzati al riconoscimento, evitando un'incompatibilità fra il decoder di file di faster-whisper 1.2.1 e il parametro metadata_errors di PyAV 19. L'applicazione usava già campioni in memoria.

## Verifiche

- **41 test Python**: acquisizione, coda/disco lento, migrazioni, revisioni, profilo, token, importazione M4A/AAC reale con riconoscimento simulato, archivio, appunti troncati, download, motore locale, pacchetto e avvio rapido.
- Cinque collaudi Edge su archivi temporanei: flusso generale, appunti/esportazione/stampa, token, interfaccia/bozze/importazione, avvio rapido/metadati. Verificati ricarica, focus, risposte fuori ordine e larghezza mobile 390 pixel.
- Prova reale Base CPU INT8 su i5-1135G7 con 6 thread: 13,607 s di audio sintetico italiano, inferenza 1,794 s, caricamento 0,758 s. È una singola misura breve; errori linguistici nel [rapporto testuale](VERIFICA_TRASCRIZIONI.md).
- Normalizzazione/segmentazione di WAV sintetici da 2 e 3 ore: 62 e 93 parti, tutti i campioni conservati, risposte AI simulate. Non misura acquisizione prolungata o riconoscimento remoto.
- Dipendenze, integrità ZIP ed esclusione di configurazione privata, dati, modelli e ambienti verificati.

I test ordinari e del browser non effettuano chiamate a pagamento. Le prove reali cloud precedenti sono distinte dai test simulati. Sul secondo PC non sono ancora state eseguite installazione pulita e prova della futura GPU NVIDIA da 8/12 GB.

## Pulizia del rilascio

Documentazione consolidata: rimossi progetto preliminare superato, resoconti progressivi duplicati, vecchi conteggi dei test, annotazioni sulla chiave personale e stime di costo basate su limiti precedenti. Screenshot rigenerabili in test-artifacts, esclusi da Git e ZIP. Rimossi log storici chiusi e pacchetti di trasferimento sostituiti dalla versione numerata.

Rimosse le dipendenze dirette inutilizzate Pillow, qrcode e requests e i vincoli transitori superflui charset-normalizer/urllib3. Il lock conserva le dipendenze necessarie. Gli ambienti e i modelli rimangono locali e ignorati: sul PC corrente .venv usa l'interprete di .runtime, quindi rimuoverlo impedirebbe l'avvio.

## Limiti e prossime priorità

1. Backup automatico con prova di ripristino; oggi copia completa di data a server spento.
2. Appunti per sezioni su lezioni lunghe: oggi richiesta unica, massimo 4.000 token, timeout 90 s e rifiuto delle uscite incomplete.
3. Confronto sullo stesso audio reale per OpenAI, Turbo e Large v3. Nessuna percentuale di accuratezza senza riferimento. Collaudo microfono/GPU sul PC destinatario.
4. Controllo dei conflitti fra editor in più schede: le revisioni riducono le letture ma non impediscono tutte le sovrascritture concorrenti.
5. Separazione ulteriore di persistenza e orchestrazione quando nuove funzioni lo richiederanno.

Nessuna diarizzazione, allegato documentale, ricerca nel corpo dei testi o sincronizzazione; timestamp per segmento. L'importazione legacy identifica i file tramite percorso: ricopiarli altrove può duplicare lezioni già migrate. Nessuna modifica a driver, impostazioni del sistema o altri progetti.
