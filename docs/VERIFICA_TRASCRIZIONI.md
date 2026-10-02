# Verifica dell'uscita testuale

Controllo del 2 ottobre 2026. L'utente considera buona la trascrizione OpenAI: resta il motore iniziale. Il controllo seguente legge l'archivio senza correggere o rigenerare le lezioni. Non è una valutazione automatica di accuratezza rispetto a una trascrizione umana dell'audio.

## Risultati presenti nell'archivio

| Campione | Motore | Audio | Parti concluse | Caratteri della trascrizione |
| --- | --- | ---: | ---: | ---: |
| Ciclo dell'acqua, voce sintetica | OpenAI | 13,61 s | 1/1 | 184 |
| Ciclo dell'acqua, stessa voce sintetica | Locale Base | 13,61 s | 1/1 | 184 |
| Grafica Multimediale 01 | Locale Base | 23,62 s | 1/1 | 309 |
| Grafica Multimediale 02 | OpenAI | 122,11 s | 2/2 | 1.947 |
| 01 - Introduzione | OpenAI, lezione preparata | 0 s | Nessuna | 0 |

I caratteri includono i riferimenti temporali. Nella lezione da 122,11 secondi la parte da 0 a 120 secondi contiene 1.939 caratteri riconosciuti; l'ultima parte di 2,11 secondi è completata ma restituisce testo vuoto. Questo non dimostra che l'ultima parte sia silenzio: va riascoltata per distinguere una coda senza parlato da una possibile omissione.

## Lettura qualitativa

Sul campione sintetico, OpenAI restituisce correttamente «Il vapore sale […] e forma le nuvole», mentre Base produce «Il vapor e sale» e «formale nuvole». A parità di numero di caratteri, la qualità è diversa: la lunghezza del risultato non misura l'accuratezza.

Nell'estratto locale di grafica compaiono formulazioni poco comprensibili come «grafi design», «un far sui miei coperchi» e «sotturato». Questo Base non è un riferimento qualitativo sufficiente per appunti specialistici senza revisione. Non è stato confrontato con i modelli locali maggiori.

Il testo OpenAI di grafica è più leggibile e articolato. Espressioni come «una presentazione grafica manuale», «un risultato economico» e «linguaggio comprensibile ed impatto» meritano un controllo ascoltando il punto corrispondente: la plausibilità di una correzione non prova cosa sia stato pronunciato. Non sono state applicate sostituzioni automatiche. Gli estratti locali e cloud di grafica hanno durata diversa e non costituiscono un confronto controllato dello stesso audio.

## Miglioramento dell'impaginazione

Le nuove trascrizioni vengono ricomposte con spazi regolari e paragrafi separati fra frasi, con una dimensione indicativa di 600 caratteri. Una singola frase lunga può superare tale misura. Non si modificano parole, punteggiatura o contenuto; non si inventano titoli o correzioni. Il testo restituito dal riconoscimento resta conservato anche nelle singole parti.

I riferimenti temporali identificano l'inizio della parte audio, non la posizione esatta di ogni parola. Oltre un'ora vengono mostrati come `[01:01:01]`. Le parti concluse senza testo non aggiungono righe vuote con timestamp. Le trascrizioni preesistenti e quelle già modificate a mano non vengono riscritte da questa modifica del programma.

Per rivedere un testo esistente: aprire la lezione, riascoltare con il lettore audio, correggere nella scheda Trascrizione e salvare prima di generare gli appunti. Il menu unico **Esporta** contiene Trascrizione TXT, Appunti TXT, Appunti Markdown, Appunti Stampa/PDF e audio originale quando disponibili. I formati testuali scaricano la versione salvata; con modifiche pendenti il documento interessato va prima salvato. Stampa/PDF riguarda gli appunti, anche se il menu viene aperto dalla trascrizione.

## Misura locale ripetuta

PC attuale: Intel i5-1135G7, 4 core/8 processori logici, circa 23,7 GiB RAM. Prova del comando `verifica_locale.py`, Base già sul disco, CPU INT8, 6 thread, sul campione sintetico italiano di 13,607 secondi:

| Misura | Risultato |
| --- | ---: |
| Caricamento modello | 0,758 s |
| Normalizzazione | 0,029 s |
| Inferenza e raccolta del testo | 1,794 s |
| Tempo inferenza / durata audio | 0,132 |
| Testo, senza timestamp | 176 caratteri |

Una singola prova breve, senza download: non è una stima delle prestazioni in aula, su ore di registrazione o su altri modelli. Gli errori «vapor e» e «formale nuvole» si ripresentano. Il rapporto favorevole di velocità non risolve gli errori linguistici. Il report grezzo è conservato localmente in `data/validation/locale-base-1790954408010745400.json`, insieme al TXT; i dati personali e di validazione non sono inclusi nello ZIP del programma.

## Collaudo da completare con il nuovo PC

1. Usare lo stesso audio reale di 2–5 minuti per OpenAI, Turbo e Large v3, includendo lessico tecnico, nomi e numeri.
2. Preparare una trascrizione di riferimento ascoltando l'audio. Annotare parole errate, omissioni e aggiunte; senza riferimento non riportare percentuali di accuratezza o WER.
3. Misurare caricamento, inferenza e memoria GPU separatamente; ripetere sullo stesso dispositivo e indicare configurazione e modello.
4. Verificare coda finale, pause, confini fra parti e registrazione prolungata. Controllare che nomi o frasi a cavallo delle parti non siano persi o duplicati.
5. Generare appunti solo dopo la revisione e controllare che non aggiungano informazioni assenti nella lezione.

Non sono state effettuate nuove chiamate OpenAI in questo intervento. La prova sulla futura GPU da 8/12 GB e l'ascolto sistematico dei file reali restano da completare. Per i comandi consultare la [guida del nuovo PC](INSTALLAZIONE_ALTRO_PC.md).
