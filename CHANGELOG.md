# Note di versione

## 2.0.0 — 2 ottobre 2026

Prima versione dell'applicazione web locale completa, successiva al prototipo Tkinter.

### Funzioni

- Archivio SQLite persistente, profilo docente e classi, ricerca nei metadati, archiviazione, cestino e ripristino.
- Interfaccia chiara, dialoghi accessibili da tastiera, bozze persistenti del profilo/creazione e adattamento mobile.
- Registrazione con pausa/ripresa e salvataggio su disco; avvio immediato senza dati preliminari e compilazione successiva.
- Importazione audio, normalizzazione, lettore e trascrizione differita a segmenti con recupero.
- OpenAI iniziale; faster-whisper con Base, Small, Medium, Large v3 Turbo e Large v3 su CPU o NVIDIA configurabile.
- Trascrizione modificabile, appunti strutturati con lettura/editor, TXT/Markdown, stampa/PDF e audio in un solo menu Esporta.
- Installer Windows, diagnosi locale, pacchetto dei sorgenti e guida al trasferimento dell'archivio.

### Affidabilità e ottimizzazioni

- Scrittura audio in coda limitata su thread dedicato, errori visibili e drenaggio finale.
- Riepiloghi leggeri, revisioni, polling adattivo e protezione dalle risposte tardive del browser.
- Corretto il blocco del profilo dovuto a template/script di versioni diverse; recupero controllato del token.
- Paragrafi senza riscrivere le parole; appunti vuoti o troncati rifiutati conservando i precedenti.
- Un solo modello locale in memoria e hardware configurabile, senza ripiego silenzioso sulla CPU.
- Versione unificata, documentazione consolidata, dipendenze inutilizzate rimosse, artefatti e dati esclusi dal controllo versione.

### Compatibilità e migrazione

- Database preesistenti aggiornati automaticamente; audio, profilo e testi conservati. Backup a server spento prima di un trasferimento.
- Tkinter ancora avviabile con --desktop; il web è l'interfaccia predefinita.
- Sul nuovo PC ricreare Python e trasferire data separatamente. Lo ZIP esclude segreti, lezioni, librerie e modelli.

Verifiche e limiti residui nello [stato tecnico](docs/STATO_PROGETTO.md). Tag di rilascio: v2.0.0.
