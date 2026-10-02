"""Archivio persistente e lavorazioni audio per il pannello web locale."""
import json
import queue
import shutil
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from app_errors import error_message
from audio_capture import BufferedAudioWriter
from audio_processing import normalize_audio
from local_runtime import LOCAL_MODELS, LocalRuntime, load_local_model
from transcript_tools import compose_transcript
from demo_client import DEMO_SEGMENTS, DemoAIClient


class LessonService:
    def __init__(self, root, api_key="", client_factory=None, local_runtime=None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key.strip()
        self.client_factory = client_factory
        self.local_runtime = local_runtime or LocalRuntime.from_config()
        self.lock = threading.RLock()
        self.recording = None
        self.local_models = {}
        self.jobs = queue.Queue()
        with self.connection() as db:
            db.execute("CREATE TABLE IF NOT EXISTS lessons (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            if "summary" not in {row[1] for row in db.execute("PRAGMA table_info(lessons)")}:
                db.execute("ALTER TABLE lessons ADD COLUMN summary TEXT")
            for lesson_id, payload in db.execute("SELECT id, payload FROM lessons WHERE summary IS NULL").fetchall():
                lesson = json.loads(payload)
                db.execute("UPDATE lessons SET summary=? WHERE id=?",
                           (json.dumps(self.summary(lesson), ensure_ascii=False), lesson_id))
            db.execute("CREATE TABLE IF NOT EXISTS deleted_lessons (id TEXT PRIMARY KEY)")
            db.execute("CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        for lesson in self.list_lessons():
            if lesson["status"] in ("recording", "paused", "transcribing", "queued", "notes"):
                self.update(lesson["id"], status="interrupted", error="Sessione interrotta. L'audio salvato può essere ritrascritto.")
        self.thread = threading.Thread(target=self.run_jobs, daemon=True)
        self.thread.start()

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.root / "archive.sqlite3", timeout=15)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def list_lessons(self):
        with self.lock, self.connection() as db:
            lessons = [json.loads(row[0]) for row in db.execute("SELECT payload FROM lessons")]
        return sorted(lessons, key=lambda item: item["created_at"], reverse=True)

    @staticmethod
    def summary(lesson):
        return {key: value for key, value in lesson.items()
                if key not in ("transcript", "notes", "segments")}

    def list_summaries(self):
        """Il polling non carica trascrizioni e segmenti di tutte le lezioni."""
        with self.lock, self.connection() as db:
            lessons = [json.loads(row[0]) for row in db.execute("SELECT summary FROM lessons")]
        return sorted(lessons, key=lambda item: item["created_at"], reverse=True)

    def get(self, lesson_id):
        with self.lock, self.connection() as db:
            row = db.execute("SELECT payload FROM lessons WHERE id=?", (lesson_id,)).fetchone()
        if not row:
            raise KeyError("Lezione non trovata")
        return json.loads(row[0])

    def put(self, lesson):
        with self.lock, self.connection() as db:
            lesson["revision"] = uuid.uuid4().hex
            db.execute("INSERT OR REPLACE INTO lessons (id, payload, summary) VALUES (?, ?, ?)",
                       (lesson["id"], json.dumps(lesson, ensure_ascii=False),
                        json.dumps(self.summary(lesson), ensure_ascii=False)))
        return lesson

    def update(self, lesson_id, **fields):
        with self.lock:
            lesson = self.get(lesson_id)
            lesson.update(fields)
            return self.put(lesson)

    def create(self, fields):
        fields = dict(fields)
        assignment = None
        if fields.get("assignment_id"):
            profile = self.get_profile()
            assignment = next((item for item in profile.get("assignments", []) if item["id"] == fields["assignment_id"]), None)
            if not assignment:
                raise ValueError("Seleziona una classe presente nel profilo docente.")
            fields.update(docente=profile["name"], materia=assignment["teaching"])
        title = str(fields.get("title", "")).strip()[:200]
        if not title:
            raise ValueError("Inserisci il titolo della lezione.")
        engine = fields.get("engine", "local")
        model = fields.get("model") or ("base" if engine == "local" else "gpt-transcribe")
        if engine not in ("local", "openai", "demo"):
            raise ValueError("Motore di trascrizione non valido.")
        allowed = {"local": LOCAL_MODELS, "openai": ("gpt-transcribe", "gpt-4o-transcribe", "gpt-4o-mini-transcribe", "whisper-1"), "demo": ("demo",)}
        if engine == "demo":
            model = "demo"
        if model not in allowed[engine]:
            raise ValueError("Modello non valido per il motore selezionato.")
        lesson = {"id": uuid.uuid4().hex, "title": title, "docente": str(fields.get("docente", ""))[:200],
                  "materia": str(fields.get("materia", ""))[:200], "created_at": datetime.now().astimezone().isoformat(),
                  "status": "prepared", "collection": "active", "engine": engine, "model": model, "transcript": "", "notes": "",
                  "segments": [], "error": "", "audio": None, "duration": 0, "progress": "Lezione pronta."}
        if assignment:
            lesson.update(assignment_id=assignment["id"], course=assignment["course"],
                          teaching=assignment["teaching"], year=assignment["year"], section=assignment["section"])
        (self.root / lesson["id"]).mkdir()
        return self.put(lesson)

    def get_profile(self):
        with self.lock, self.connection() as db:
            row = db.execute("SELECT payload FROM settings WHERE name='teacher'").fetchone()
        return json.loads(row[0]) if row else {"name":"", "assignments":[]}

    def quick_start(self, demo=False):
        """Creazione e avvio sotto lo stesso lock: nessuna seconda sessione concorrente."""
        with self.lock:
            if self.recording:
                raise ValueError("È già in corso una registrazione. Aprila per continuare.")
            lesson = self.create({"title": "Registrazione del " + datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                                  "engine": "demo" if demo else "openai",
                                  "docente": self.get_profile().get('name', '')})
            self.update(lesson['id'], metadata_pending=True)
            try:
                return self.start(lesson['id'])
            except Exception as exc:
                # Resta selezionabile e riutilizzabile dopo la scelta di un microfono.
                return self.update(lesson['id'], error=error_message(exc),
                                   progress="Registrazione non avviata. Controlla il microfono e premi Registra.")

    def save_metadata(self, lesson_id, fields):
        with self.lock:
            lesson = self.get(lesson_id)
            self.require_editable(lesson)
            if lesson['status'] == 'notes':
                raise ValueError("Attendi la fine della generazione degli appunti prima di modificare i dati.")
            keys = ('title', 'docente', 'course', 'materia', 'year', 'section')
            values = {key: str(fields.get(key, lesson.get(key, ''))).strip() for key in keys}
            if not values['title'] or any(len(value) > 200 for value in values.values()):
                raise ValueError("Inserisci un titolo e usa al massimo 200 caratteri per ogni campo.")
            if values['year'] and (not values['year'].isdigit() or not 1 <= int(values['year']) <= 10):
                raise ValueError("L'anno deve essere un numero da 1 a 10 oppure vuoto.")
            return self.update(lesson_id, **values, teaching=values['materia'], assignment_id=None,
                               metadata_pending=not all(values.values()))

    def save_profile(self, fields):
        name = str(fields.get("name", "")).strip()
        assignments = fields.get("assignments")
        if not name or len(name) > 200:
            raise ValueError("Inserisci il nome del docente (massimo 200 caratteri).")
        if not isinstance(assignments, list) or not 1 <= len(assignments) <= 100:
            raise ValueError("Aggiungi almeno un insegnamento con anno e sezione (massimo 100).")
        entries, seen, ids = [], set(), set()
        for item in assignments:
            if not isinstance(item, dict):
                raise ValueError("Dati dell'insegnamento non validi.")
            values = {key:str(item.get(key, "")).strip() for key in ("course", "teaching", "year", "section")}
            if any(not value or len(value) > 200 for value in values.values()):
                raise ValueError("Completa corso, insegnamento, anno e sezione di ogni riga.")
            if not values["year"].isdigit() or not 1 <= int(values["year"]) <= 10:
                raise ValueError("L'anno deve essere un numero da 1 a 10.")
            values["year"] = str(int(values["year"]))
            signature = tuple(value.casefold() for value in values.values())
            if signature in seen:
                raise ValueError("Questo corso, insegnamento e classe sono già presenti.")
            seen.add(signature)
            entry_id = str(item.get("id") or uuid.uuid4().hex)
            if len(entry_id) != 32 or any(c not in '0123456789abcdef' for c in entry_id) or entry_id in ids:
                raise ValueError("Identificativo dell'insegnamento non valido.")
            ids.add(entry_id)
            entries.append(dict(id=entry_id, **values))
        profile = {"name":name, "assignments":entries}
        with self.lock, self.connection() as db:
            db.execute("INSERT OR REPLACE INTO settings VALUES ('teacher', ?)", (json.dumps(profile, ensure_ascii=False),))
        return profile

    def require_editable(self, lesson):
        if lesson.get("collection", "active") != "active":
            raise ValueError("Riporta la lezione in Lezioni prima di modificarla o elaborarla.")

    def move(self, lesson_id, destination):
        if destination not in ("active", "archived", "trash"):
            raise ValueError("Destinazione non valida.")
        with self.lock:
            lesson = self.get(lesson_id)
            if lesson["status"] in ("recording", "paused", "queued", "transcribing", "notes"):
                raise ValueError("Attendi la fine della registrazione o della lavorazione prima di spostare la lezione.")
            return self.update(lesson_id, collection=destination,
                               collection_changed_at=datetime.now().astimezone().isoformat())

    def delete_permanently(self, lesson_id):
        with self.lock:
            lesson = self.get(lesson_id)
            if lesson.get("collection") != "trash":
                raise ValueError("Sposta prima la lezione nel cestino.")
            if lesson["status"] in ("recording", "paused", "queued", "transcribing", "notes"):
                raise ValueError("La lezione ha una lavorazione in corso.")
            folder = (self.root / lesson_id).resolve()
            if folder.parent != self.root or len(lesson_id) != 32 or any(c not in '0123456789abcdef' for c in lesson_id):
                raise ValueError("Percorso della lezione non valido.")
            if folder.exists():
                shutil.rmtree(folder)
            with self.connection() as db:
                # L'importazione automatica non deve far ricomparire lezioni eliminate.
                db.execute("INSERT OR IGNORE INTO deleted_lessons VALUES (?)", (lesson_id,))
                db.execute("DELETE FROM lessons WHERE id=?", (lesson_id,))

    def devices(self):
        try:
            return [{"id": index, "name": device["name"], "default": index == sd.default.device[0]}
                    for index, device in enumerate(sd.query_devices()) if device["max_input_channels"] > 0]
        except Exception:
            return []

    def start(self, lesson_id, device=None):
        with self.lock:
            if self.recording:
                raise ValueError("È già in corso una registrazione.")
            lesson = self.get(lesson_id)
            self.require_editable(lesson)
            if lesson["status"] != "prepared":
                raise ValueError("Crea una nuova lezione per registrare altro audio.")
            record = {"id": lesson_id, "paused": False, "level": 0, "frames": 0, "rate": 16000, "error": ""}
            if lesson["engine"] != "demo":
                if device is not None:
                    device = int(device)
                try:
                    sd.check_input_settings(device=device, samplerate=16000, channels=1, dtype="float32")
                except sd.PortAudioError:
                    record["rate"] = int(sd.query_devices(device, "input")["default_samplerate"])
                record["writer"] = BufferedAudioWriter(self.root / lesson_id / "recording.wav", record["rate"])
                def callback(indata, frames, time_info, status):
                    if record["paused"]:
                        record["level"] = 0
                        return
                    if not record["writer"].submit(indata[:, 0]):
                        record["error"] = record["writer"].error
                        raise sd.CallbackAbort
                    record["frames"] += frames
                    record["level"] = float(np.sqrt(np.mean(indata ** 2)))
                    if status:
                        record["error"] = "Il microfono segnala un'interruzione audio."
                try:
                    record["stream"] = sd.InputStream(device=device, samplerate=record["rate"], channels=1,
                                                       dtype="float32", callback=callback, blocksize=1024)
                    record["stream"].start()
                except Exception:
                    if "stream" in record:
                        record["stream"].close()
                    record["writer"].close()
                    raise
            self.recording = record
            return self.update(lesson_id, status="recording", audio=None if lesson["engine"] == "demo" else "recording.wav", error="", progress="Audio in registrazione; trascrizione dopo l'arresto.")

    def pause(self, lesson_id):
        with self.lock:
            if not self.recording or self.recording["id"] != lesson_id:
                raise ValueError("Nessuna registrazione attiva per questa lezione.")
            self.recording["paused"] = not self.recording["paused"]
            return self.update(lesson_id, status="paused" if self.recording["paused"] else "recording")

    def stop(self, lesson_id):
        with self.lock:
            record = self.recording
            if not record or record["id"] != lesson_id:
                raise ValueError("Nessuna registrazione attiva per questa lezione.")
            record["paused"] = True
            try:
                if "stream" in record:
                    try:
                        record["stream"].stop()
                    finally:
                        record["stream"].close()
            finally:
                if "writer" in record:
                    record["writer"].close()
                    record["frames"] = record["writer"].frames
                    record["error"] = record["writer"].error or record["error"]
                self.recording = None
            self.update(lesson_id, duration=record["frames"] / record["rate"], capture_warning=record["error"])
            return self.enqueue(lesson_id, "transcribe")

    def enqueue(self, lesson_id, action):
        with self.lock:
            lesson = self.get(lesson_id)
            self.require_editable(lesson)
            if lesson["status"] in ("recording", "paused", "queued", "transcribing", "notes"):
                if not (action == "transcribe" and self.recording is None and lesson["status"] in ("recording", "paused")):
                    raise ValueError("Questa lezione ha già un'operazione in corso.")
            if action == "notes" and not lesson["transcript"].strip():
                raise ValueError("Serve una trascrizione prima di generare gli appunti.")
            if action == "transcribe" and not lesson["audio"] and lesson["engine"] != "demo":
                raise ValueError("Questa lezione non contiene audio da trascrivere.")
            self.update(lesson_id, status="queued", error="", progress="Lavorazione in coda...")
            self.jobs.put((lesson_id, action))
            return self.get(lesson_id)

    def import_audio(self, lesson_id, uploaded):
        lesson = self.get(lesson_id)
        self.require_editable(lesson)
        if lesson["status"] != "prepared":
            raise ValueError("Importa l'audio in una nuova lezione.")
        suffix = Path(uploaded.filename or "").suffix.lower()
        if suffix not in (".wav", ".mp3", ".mp4", ".m4a", ".webm", ".ogg", ".flac", ".mpeg", ".mpga"):
            raise ValueError("Formato audio non supportato.")
        filename = "imported" + suffix
        uploaded.save(self.root / lesson_id / filename)
        self.update(lesson_id, audio=filename)
        return self.enqueue(lesson_id, "transcribe")

    def save_text(self, lesson_id, transcript=None, notes=None):
        with self.lock:
            lesson = self.get(lesson_id)
            self.require_editable(lesson)
            if lesson["status"] in ("recording", "paused", "queued", "transcribing", "notes"):
                raise ValueError("Attendi la fine della lavorazione prima di modificare il testo.")
            fields = {}
            if transcript is not None:
                fields["transcript"] = str(transcript)
            if notes is not None:
                fields["notes"] = str(notes)
            updated = self.update(lesson_id, **fields)
            self.export_text(updated)
            return updated

    def export_text(self, lesson):
        for name in ("transcript", "notes"):
            target = self.root / lesson["id"] / (name + ".txt")
            temporary = target.with_suffix(".tmp")
            temporary.write_text(lesson[name], encoding="utf-8")
            temporary.replace(target)

    def cloud_client(self):
        if not self.api_key or self.api_key == "sk-...":
            raise ValueError("Inserisci una chiave OpenAI valida in config.py oppure usa la trascrizione locale.")
        if self.client_factory:
            return self.client_factory()
        from openai import OpenAI
        return OpenAI(api_key=self.api_key, timeout=90, max_retries=1)

    def prepare_segments(self, lesson):
        folder = self.root / lesson["id"]
        source = folder / lesson["audio"]
        normalized = folder / "normalized.wav"
        normalize_audio(source, normalized)
        segments = []
        with sf.SoundFile(normalized) as audio:
            start = 0
            while start < len(audio):
                audio.seek(start)
                data = audio.read(16000 * 120, dtype="float32")
                cut = len(data)
                if cut == 16000 * 120 and start + cut < len(audio):
                    for position in range(cut - 8000, cut - 16000 * 8, -8000):
                        if np.sqrt(np.mean(data[position:position + 8000] ** 2)) < 0.003:
                            cut = position + 8000
                            break
                name = f"segment_{len(segments):05d}.wav"
                sf.write(folder / name, data[:cut], 16000, subtype="PCM_16")
                segments.append({"file": name, "start": start / 16000, "duration": cut / 16000, "text": "", "done": False})
                start += cut
            duration = len(audio) / 16000
        self.update(lesson["id"], segments=segments, duration=duration)
        return segments

    def transcribe(self, lesson):
        lesson_id = lesson["id"]
        self.update(lesson_id, status="transcribing", progress="Preparo l'audio...", error="")
        if lesson["engine"] == "demo":
            text = "\n\n".join(DEMO_SEGMENTS)
            self.update(lesson_id, transcript=text, status="ready", progress="Prova simulata completata.")
            self.export_text(self.get(lesson_id))
            return
        segments = lesson["segments"] or self.prepare_segments(lesson)
        if lesson["engine"] == "local":
            self.update(lesson_id, progress=f"Carico Whisper {lesson['model']}. Al primo uso il modello viene scaricato.")
            if lesson["model"] not in self.local_models:
                # La coda elabora un solo lavoro: tenere più modelli spreca RAM.
                self.local_models.clear()
                self.local_models[lesson["model"]] = load_local_model(lesson["model"], self.root / "models", self.local_runtime)
            model = self.local_models[lesson["model"]]
        else:
            client = self.cloud_client()
        for index, segment in enumerate(segments):
            if segment["done"]:
                continue
            self.update(lesson_id, progress=f"Trascrivo la parte {index + 1} di {len(segments)}...")
            path = self.root / lesson_id / segment["file"]
            if lesson["engine"] == "local":
                waveform, _ = sf.read(path, dtype="float32")
                result, _ = model.transcribe(waveform, language="it", vad_filter=True, beam_size=5)
                text = " ".join(item.text.strip() for item in result).strip()
            else:
                with path.open("rb") as audio:
                    params = {"file": audio, "model": lesson["model"], "prompt": "Lezione in italiano. " + lesson["materia"]}
                    if lesson["model"] == "gpt-transcribe":
                        params["extra_body"] = {"languages": ["it"]}
                    else:
                        params["language"] = "it"
                    text = client.audio.transcriptions.create(**params).text.strip()
            segment.update(text=text, done=True)
            transcript = compose_transcript(segments)
            self.update(lesson_id, segments=segments, transcript=transcript)
            self.export_text(self.get(lesson_id))
        text = self.get(lesson_id)["transcript"]
        self.update(lesson_id, status="ready", progress="Trascrizione salvata." if text else "Audio salvato; nessun parlato riconosciuto.")

    def generate_notes(self, lesson):
        self.update(lesson["id"], status="notes", progress="Genero gli appunti...")
        if lesson["engine"] == "demo":
            notes = DemoAIClient().summarize_transcript(lesson["transcript"])
        else:
            from ai_client import AIClient
            self.cloud_client()  # Controlla la presenza della chiave anche con trascrizione locale.
            notes = AIClient(self.api_key).summarize_transcript(lesson["transcript"], context={
                key: lesson.get(key, "") for key in ("title", "docente", "materia", "course", "year", "section")
            })
        if not notes:
            raise ValueError("Il servizio non ha restituito appunti.")
        old = self.root / lesson["id"] / "notes.txt"
        if old.exists() and old.stat().st_size:
            (old.parent / f"notes_{datetime.now().strftime('%Y%m%d_%H%M%S%f')}.txt").write_text(old.read_text(encoding="utf-8"), encoding="utf-8")
        self.update(lesson["id"], notes=notes, status="ready", progress="Appunti salvati; pronti per la revisione.")
        self.export_text(self.get(lesson["id"]))

    def run_jobs(self):
        while True:
            lesson_id, action = self.jobs.get()
            try:
                if action == "shutdown":
                    return
                lesson = self.get(lesson_id)
                (self.transcribe if action == "transcribe" else self.generate_notes)(lesson)
            except Exception as exc:
                message = str(exc) if isinstance(exc, ValueError) else error_message(exc)
                self.update(lesson_id, status="failed", error=message, progress="Operazione fallita. L'audio e il testo già salvati sono conservati.")
            finally:
                self.jobs.task_done()

    def status(self):
        with self.lock:
            record = self.recording
            return {"recording_id": record["id"] if record else None, "paused": record["paused"] if record else False,
                    "level": record["level"] if record else 0, "duration": record["frames"] / record["rate"] if record else 0,
                    "capture_error": (getattr(record.get("writer"), "error", "") or record["error"]) if record else "",
                    "api_key_present": bool(self.api_key and self.api_key != "sk-..."),
                    "local_runtime": self.local_runtime.public()}

    def import_legacy(self, transcripts_dir, notes_dir):
        for path in Path(transcripts_dir).glob("trascrizione_*.txt"):
            legacy_id = path.stem.removeprefix("trascrizione_")
            lesson_id = uuid.uuid5(uuid.NAMESPACE_URL, str(path.resolve())).hex
            with self.connection() as db:
                if db.execute("SELECT 1 FROM deleted_lessons WHERE id=?", (lesson_id,)).fetchone():
                    continue
            try:
                self.get(lesson_id)
                continue
            except KeyError:
                pass
            lesson = self.create({"title": legacy_id.replace("_", " "), "engine": "openai"})
            generated_id = lesson["id"]
            lesson["id"] = lesson_id
            (self.root / generated_id).rename(self.root / lesson_id)
            with self.connection() as db:
                db.execute("DELETE FROM lessons WHERE id=?", (generated_id,))
            notes = Path(notes_dir) / f"appunti_{legacy_id}.txt"
            lesson.update(status="ready", transcript=path.read_text(encoding="utf-8"), notes=notes.read_text(encoding="utf-8") if notes.exists() else "", progress="Importata dall'archivio precedente.")
            self.put(lesson)
            self.export_text(lesson)

    def close(self):
        if self.recording:
            self.stop(self.recording["id"])
        self.jobs.put((None, "shutdown"))
        self.thread.join(timeout=5)
