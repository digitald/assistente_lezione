# Assistente Lezione 2.0 — Documento di progettazione

- Versione documento: 1.0
- Versione applicativa di riferimento: 2.0
- Data: 30 settembre 2026
- Stato: proposta di riferimento per l'implementazione; funzionalità non ancora realizzate

## 1. Obiettivo e destinatari

Trasformare il prototipo di registrazione e riassunto in un pannello desktop per il docente: preparare una lezione, acquisire audio e materiali, revisionare la trascrizione, generare appunti e distribuirli come documento formattato.

Il percorso principale è: **crea lezione → registra o importa audio → aggiungi materiali → revisiona trascrizione → genera e revisiona appunti → esporta**.

Il primo rilascio privilegia un singolo docente e un archivio locale. Account multiutente, sincronizzazione cloud, pubblicazione automatica e AI locale restano fuori dal perimetro iniziale.

## 2. Stato del progetto e problemi rilevati

La versione presente nel repository usa Python e Tkinter per l'interfaccia, sounddevice/soundfile/NumPy per l'audio e le API OpenAI per trascrizioni e appunti. L'archivio consiste in file di testo nelle cartelle `transcripts/` e `notes/`.

| Area | Implementazione attuale | Limite da risolvere |
| --- | --- | --- |
| Audio | Buffer circolare; invio degli ultimi quattro secondi | Il buffer non consuma i blocchi elaborati: possibili duplicazioni e perdita di parlato |
| Sessioni | Stato globale condiviso | Una risposta tardiva può essere attribuita alla sessione corrente anziché a quella di origine |
| Arresto | Salvataggio immediato della trascrizione | Non attende il completamento delle lavorazioni; possibile perdita della parte finale |
| Chiusura | Terminazione con `os._exit(0)` | Interrompe le lavorazioni senza una procedura di recupero |
| Interfaccia | Generazione in un thread secondario con aggiornamenti diretti ai widget | Aggiornamenti da trasferire al thread dell'interfaccia |
| Archivio | Metadati ricavati dal nome file; ID con precisione al minuto | Collisioni e interpretazione ambigua dei nomi composti |
| Appunti | Un'unica richiesta testuale, uscita limitata a 2.000 token | Sintesi troppo breve per lezioni lunghe; nessuno storico o editor integrato |
| Materiali | Pillow e qrcode nelle dipendenze | Nessun flusso implementato per immagini, grafici o link |
| Installazione | Dipendenze senza versioni e documentazione incompleta | Ambiente non riproducibile; nome del template di configurazione inesatto nel README |

L'analisi è basata sul codice e sulla documentazione dei servizi. Non sono state eseguite registrazioni o chiamate API. Nel terminale esaminato Python non è disponibile e il repository non contiene `config.py`.

## 3. Perimetro della prima versione 2.0

### 3.1 Pannello e gestione lezioni

- Elenco lezioni con ricerca per titolo e filtri per corso, classe, data e stato.
- Creazione e modifica di titolo, docente, materia/corso, classe, argomento, obiettivi e data.
- Una registrazione attiva alla volta; lavorazioni terminate o pendenti consultabili per lezione.
- Scheda lezione con sezioni **Trascrizione**, **Materiali**, **Appunti**, **Fonti**.
- Visualizzazione del progresso e azione di recupero quando una lavorazione fallisce.

### 3.2 Acquisizione e trascrizione

- Selezione del microfono, prova audio e indicatore del livello prima della registrazione.
- Avvio, pausa, ripresa e arresto con salvataggio progressivo dell'audio.
- Importazione di un file audio nei formati supportati dal servizio scelto.
- Trascrizione ordinata per segmenti con riferimenti temporali relativi alla registrazione.
- Modifica del testo nel pannello, preservando la versione originale della trascrizione.
- Recupero dopo perdita di connessione, errore del servizio o riavvio dell'applicazione.

### 3.3 Appunti e revisione

- Formati iniziali: sintesi e appunti dettagliati.
- Struttura: argomenti, concetti chiave, definizioni, esempi e riepilogo, quando presenti nelle fonti.
- Elaborazione per sezioni delle lezioni lunghe e composizione finale con controllo della copertura.
- Collegamenti ai segmenti o materiali utilizzati; passaggi incerti segnalati al docente.
- Editor integrato, salvataggio delle modifiche e nuova versione a ogni rigenerazione.
- Stato di revisione esplicito: gli appunti generati rimangono una bozza fino alla revisione del docente.

### 3.4 Immagini, link ed esportazione

- Caricamento di immagini e foto della lavagna, con anteprima, didascalia e associazione alla lezione o a una sezione degli appunti.
- Inserimento manuale di link con titolo, URL e nota del docente.
- Esportazione Markdown con cartella allegati e PDF con immagini, didascalie e link cliccabili.
- Conservazione della provenienza di ogni materiale e distinzione tra contenuti della lezione e integrazioni del docente.

L'analisi AI delle immagini e la ricerca online non sono requisiti del primo rilascio; il modello dati deve permetterne l'aggiunta.

## 4. Esperienza del docente

La schermata iniziale presenta il pulsante **Nuova lezione**, l'archivio filtrabile e le lezioni da completare. La scheda lezione mantiene visibili titolo, stato e azione successiva.

Durante la registrazione mostra durata, livello del microfono, pausa e arresto. Lo stato dell'audio rimane distinto da quello della trascrizione: il docente deve poter capire che la registrazione continua anche se il servizio AI non risponde.

Dopo l'arresto presenta il progresso delle trascrizioni residue. La generazione degli appunti usa una versione completa e salvata della trascrizione; non parte mentre questa è ancora in finalizzazione.

La revisione consente di passare dal testo degli appunti alla fonte corrispondente. Esportazione e rigenerazione sono azioni distinte; una nuova generazione non sovrascrive le modifiche del docente.

## 5. Architettura proposta

Mantenere inizialmente Python e Tkinter, usando componenti e stili coerenti. La scelta di un'altra interfaccia verrà valutata solo se una prova dell'editor e dell'anteprima documentale mostra limiti sostanziali.

| Componente | Responsabilità |
| --- | --- |
| Interfaccia | Pannello, editor, comandi e visualizzazione degli eventi |
| Servizio lezioni | Metadati, transizioni di stato e coordinamento delle operazioni |
| Acquisizione audio | Dispositivi, registrazione su disco e segmentazione |
| Coda lavorazioni | Trascrizioni e generazioni ordinate, recuperi e stato persistente |
| Adattatore AI | Chiamate al provider, modelli configurabili, timeout e gestione degli errori |
| Archivio | SQLite per metadati e stato; filesystem per audio e allegati |
| Esportazione | Composizione Markdown/PDF a partire da una versione salvata |

L'interfaccia comunica con i worker tramite code di eventi, lette dal ciclo Tkinter. I worker non modificano direttamente i widget. Si sostituisce progressivamente lo stato globale di `shared_state.py` con oggetti e operazioni del servizio lezioni.

Le dipendenze devono avere versioni collaudate e un'installazione riproducibile. La chiave API rimane fuori da repository e database; le impostazioni non sensibili possono essere salvate localmente. La versione Python supportata va dichiarata dopo il collaudo: il requisito attuale di Python 3.8 non è coerente con l'annotazione `str | None` presente nel codice senza rinvio delle annotazioni.

## 6. Modello dati e archivio

| Entità | Dati principali |
| --- | --- |
| Lezione | UUID, titolo, docente, corso, classe, argomento, obiettivi, date e stato |
| Registrazione | Lezione, percorso audio, formato, durata, dispositivo e stato |
| Segmento | Registrazione, indice, intervallo temporale, stato e testo originale |
| Revisione trascrizione | Lezione, versione, testo corretto, data e riferimenti ai segmenti |
| Versione appunti | Lezione, formato, contenuto, revisione della trascrizione, modello, versione prompt e stato di revisione |
| Materiale | Lezione, file, tipo, didascalia, origine e posizione negli appunti |
| Fonte | Lezione, titolo, URL, nota, origine manuale/ricerca e data di consultazione se applicabile |
| Lavorazione | Tipo, riferimento sorgente, stato, tentativi, errore e date |

Cartella dati proposta: database, audio, materiali ed esportazioni in una directory applicativa configurabile, separata dalla cartella del codice. Il database conserva percorsi relativi quando possibile.

La migrazione importa i file esistenti senza modificarli, assegna UUID e conserva l'identificativo originale. I metadati non ricostruibili con certezza restano da confermare nel pannello. L'importazione deve essere ripetibile senza creare duplicati.

## 7. Stati e affidabilità

Gli stati sono separati per non confondere lezione, registrazione e lavorazioni:

- Lezione: preparata, in corso, da revisionare, completata.
- Registrazione: inattiva, in registrazione, in pausa, in finalizzazione, salvata, interrotta.
- Lavorazione: in attesa, in corso, completata, fallita, annullata.
- Appunti: bozza AI, modificati, revisionati.

Regole obbligatorie:

1. Ogni blocco acquisito ha ID della registrazione, indice e tempi assegnati prima della chiamata AI.
2. L'audio viene salvato prima di affidarne la trascrizione al servizio esterno.
3. Il risultato aggiorna soltanto il segmento di origine e non la sessione attualmente aperta.
4. I segmenti si ricompongono per indice, indipendentemente dall'ordine di risposta.
5. Il tratto finale più breve viene salvato e accodato all'arresto.
6. Una disconnessione mantiene registrazione e coda locale; gli errori temporanei hanno tentativi limitati e attese crescenti.
7. Il recupero di una lavorazione non duplica i risultati locali. Un timeout remoto può comunque comportare una richiesta ripetuta e relativo costo.
8. La chiusura interrompe l'acquisizione, salva il lavoro disponibile e lascia le attività incompiute recuperabili al riavvio.
9. Database e scrittura dei file devono consentire di rilevare e riconciliare operazioni interrotte.

## 8. AI integrata e aggiornamento dei servizi

L'integrazione attuale usa `whisper-1` per audio e `gpt-4o` per testo. L'elaborazione avviene nel cloud; non sono presenti modelli locali.

Alla data del documento OpenAI indica il ritiro di `whisper-1` il **26 febbraio 2027**, con `gpt-transcribe` e `gpt-live-transcribe` come sostituti. Valutare il primo per file e segmenti e il secondo se è richiesta una vera trascrizione dal vivo. La migrazione richiede verifica dei parametri, delle risposte, dell'accesso dell'account e della qualità sull'italiano.

Il prompt di Whisper va ridotto a terminologia e contesto: non segue istruzioni come un modello conversazionale e la finestra del prompt è limitata a 224 token.

Per gli appunti, rendere il modello configurabile e confrontare le alternative su una lezione campione. GPT-4o supporta input testuali e immagini, ma il codice attuale invia solo testo. Non si assume che il modello abbia consultato un link se il contenuto non viene recuperato.

Registrare modello, versione delle istruzioni e sorgenti usate per ogni generazione. Misurare durata, consumo disponibile dalla risposta API e costi stimati secondo un listino aggiornato. Non fissare nel progetto prezzi o disponibilità senza verifica.

## 9. Hardware e compatibilità

Il PC esaminato dispone di Windows 11 Pro a 64 bit, Intel Core i7-14700F (20 core), circa 32 GB di RAM e NVIDIA GeForce RTX 5060. I dispositivi audio Realtek e NVIDIA risultano presenti con stato OK.

Queste risorse sono adeguate per l'architettura cloud proposta. La GPU non è usata dall'applicazione attuale. La presenza dei dispositivi audio non certifica il funzionamento del microfono o la qualità della registrazione.

L'acquisizione attuale impone 16 kHz mono al dispositivo predefinito. La versione 2.0 deve verificare le impostazioni supportate, usare una frequenza compatibile ed eventualmente ricampionare per il servizio AI. Prevedere controllo dei permessi, scollegamento del dispositivo e soglia del silenzio configurabile o calibrata; la soglia RMS fissa attuale può escludere una voce debole.

Windows è la piattaforma del primo collaudo. macOS e Linux restano obiettivi da verificare separatamente, incluse dipendenze audio, accesso al microfono e apertura/esportazione dei documenti.

## 10. Estensioni successive

| Estensione | Comportamento e vincolo |
| --- | --- |
| Analisi visiva | Leggere lavagna e slide, collegando il risultato al materiale originale e segnalando testo o formule incerti |
| Slide/PDF | Importare materiali e collegarne pagine e immagini agli argomenti; verificare il trattamento visivo dei formati scelti |
| Grafici numerici | Usare dati o formule confermati, conservando tabella sorgente, unità, assi e metodo di calcolo; nessun valore inventato |
| Schemi concettuali | Produrre diagrammi modificabili a partire da concetti della lezione |
| Ricerca web | Recuperare fonti reali con citazioni visibili e distinguere gli approfondimenti dal contenuto della lezione |
| Immagini generate | Usare un servizio dedicato; salvare descrizione, origine AI e revisione del docente |
| AI locale | Verificare memoria video, motore, licenze, qualità e velocità prima di dichiarare supporto |

Gli appunti multimediali richiedono contenuto strutturato e riferimenti agli allegati; un unico file `.txt` non è sufficiente come formato principale.

## 11. Fasi di realizzazione

| Fase | Risultato verificabile | Dipendenza |
| --- | --- | --- |
| 0 — Validazione | Ambiente riproducibile, microfono provato, accesso API e lezione campione | Nessuna |
| 1 — Affidabilità | Audio persistente, coda per segmenti, arresto e recupero | Fase 0 |
| 2 — Archivio | Database, UUID, metadati e importazione del vecchio archivio | Fase 1 |
| 3 — Pannello | Elenco filtrabile, scheda lezione e revisione trascrizione | Fase 2 |
| 4 — Appunti | Generazione per sezioni, editor e versioni | Fasi 2–3 |
| 5 — Materiali ed export | Immagini, link manuali e documenti Markdown/PDF | Fasi 3–4 |
| 6 — Collaudo 2.0 | Percorso completo su lezioni reali e istruzioni di installazione | Fasi precedenti |

Stime di tempo e budget saranno formulate dopo la fase 0 e una prova dell'editor. Non sono ancora stati misurati velocità, costo per ora di lezione o qualità in aula.

## 12. Criteri di accettazione e prove

- **Isolamento:** una risposta tardiva della lezione A non modifica la lezione B.
- **Ordine e copertura:** una registrazione campione mantiene ordine dei segmenti e tratto finale, senza duplicati locali.
- **Disconnessione:** la registrazione continua su disco; le attività fallite possono essere riprese.
- **Riavvio:** archivio e progressi salvati sono leggibili e le lavorazioni interrotte sono riconoscibili.
- **Pausa:** il parlato durante la pausa non viene acquisito; la ripresa non reutilizza segmenti precedenti.
- **Microfono:** dispositivo assente o formato incompatibile produce un messaggio utile senza una falsa indicazione di registrazione attiva.
- **Versioni:** rigenerare appunti conserva sia la bozza precedente sia le modifiche del docente.
- **Qualità:** il docente confronta gli appunti con una lezione campione; omissioni, aggiunte non supportate e termini tecnici errati sono registrati.
- **Materiali:** immagini e link rimangono associati alla lezione dopo il riavvio e compaiono correttamente negli export.
- **Migrazione:** ripetere l'importazione non duplica lezioni e non altera i file originali.
- **Interfaccia:** lavorazioni lente non bloccano i controlli e gli aggiornamenti avvengono nel thread Tkinter.

Le prove del flusso e degli errori usano un adattatore AI simulato; qualità, latenza e costi richiedono anche prove API reali. Il PDF va controllato visivamente con immagini e link su più pagine.

## 13. Decisioni ancora da validare

- Se la trascrizione durante la lezione deve essere immediata o può procedere con ritardo controllato.
- Modello per gli appunti e modello di trascrizione disponibili nell'account del docente.
- Comportamento e qualità dell'editor/anteprima nell'interfaccia desktop.
- Politica di conservazione dell'audio e posizione dell'archivio locale.
- Formati audio di importazione e piattaforme da certificare oltre Windows.
- Costi e tempi accettabili su una lezione reale.

## 14. Fonti tecniche

Documentazione consultata il 30 settembre 2026; disponibilità e condizioni dei servizi vanno ricontrollate durante l'implementazione.

- [OpenAI — Deprecazioni](https://developers.openai.com/api/docs/deprecations)
- [OpenAI — Trascrizione audio](https://developers.openai.com/api/docs/guides/speech-to-text)
- [OpenAI — GPT-4o](https://developers.openai.com/api/docs/models/gpt-4o)
- [OpenAI — Immagini e visione](https://developers.openai.com/api/docs/guides/images-vision)
- [OpenAI — Generazione immagini](https://developers.openai.com/api/docs/guides/image-generation)
- [OpenAI — Ricerca web](https://developers.openai.com/api/docs/guides/tools-web-search)
- [sounddevice — Verifica hardware](https://python-sounddevice.readthedocs.io/en/0.5.4/api/checking-hardware.html)
