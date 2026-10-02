"""Audio su disco, coda ordinata e finalizzazione esplicita."""
import queue
import threading
from datetime import datetime
from pathlib import Path
import numpy as np
import sounddevice as sd
import soundfile as sf
import config
import shared_state
from utils import save_transcript_to_file
from app_errors import error_message


class TranscriptionWorker(threading.Thread):
    def __init__(self, ai_client, chunk_duration=4, sample_rate=16000):
        super().__init__(daemon=True)
        self.ai_client = ai_client
        self.sample_rate = sample_rate
        self.samples_per_chunk = int(sample_rate * chunk_duration)
        self.lock = threading.Lock()
        self.jobs = queue.Queue()
        self.events = queue.Queue()
        self.stream = None
        self.audio_file = None
        self.session_id = None
        self.pending = np.empty(0, dtype=np.float32)
        self.segment_index = 0
        self.level = 0.0

    def begin_session(self, session_id):
        if self.stream is not None:
            raise RuntimeError("Registrazione già attiva")
        audio_dir = Path(config.TRANSCRIPTS_DIR) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        path = audio_dir / f"audio_{session_id}.wav"
        self.session_id = session_id
        self.pending = np.empty(0, dtype=np.float32)
        self.segment_index = 0
        self.audio_file = sf.SoundFile(path, mode="w", samplerate=self.sample_rate, channels=1, subtype="PCM_16")
        try:
            self.stream = sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32",
                                         callback=self.audio_callback, blocksize=1024)
            self.stream.start()
        except Exception:
            if self.stream is not None:
                self.stream.close()
            self.stream = None
            self.audio_file.close()
            self.audio_file = None
            self.session_id = None
            raise
        shared_state.session_transcripts[session_id]["audio_path"] = str(path)

    def _enqueue(self, data):
        self.jobs.put(("segment", self.session_id, self.segment_index, data.copy()))
        self.segment_index += 1

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            self.events.put(("warning", self.session_id, "Il dispositivo segnala un'interruzione audio."))
        if not shared_state.session_active or shared_state.session_paused:
            return
        try:
            with self.lock:
                data = indata[:, 0]
                self.level = float(np.sqrt(np.mean(data ** 2)))
                self.audio_file.write(data)
                self.audio_file.flush()
                self.pending = np.concatenate((self.pending, data))
                while len(self.pending) >= self.samples_per_chunk:
                    self._enqueue(self.pending[:self.samples_per_chunk])
                    self.pending = self.pending[self.samples_per_chunk:]
        except Exception as exc:
            shared_state.session_active = False
            self.events.put(("capture_error", self.session_id, error_message(exc)))

    def finish_session(self):
        session_id = self.session_id
        if self.stream is not None:
            for operation in (self.stream.stop, self.stream.close):
                try:
                    operation()
                except Exception as exc:
                    self.events.put(("error", session_id, error_message(exc)))
            self.stream = None
        with self.lock:
            if len(self.pending):
                self._enqueue(self.pending)
                self.pending = np.empty(0, dtype=np.float32)
            if self.audio_file is not None:
                self.audio_file.close()
                self.audio_file = None
            self.session_id = None
        self.jobs.put(("finish", session_id, None, None))

    def run(self):
        while True:
            kind, session_id, index, data = self.jobs.get()
            try:
                if kind == "shutdown":
                    return
                if kind == "finish":
                    saved = save_transcript_to_file(session_id)
                    self.events.put(("finished", session_id, saved))
                    continue
                folder = Path(config.TRANSCRIPTS_DIR) / "audio" / session_id
                folder.mkdir(parents=True, exist_ok=True)
                path = folder / f"segmento_{index:06d}.wav"
                sf.write(path, data, self.sample_rate)
                if float(np.sqrt(np.mean(data ** 2))) < 0.0001:
                    continue
                self.events.put(("processing", session_id, index))
                with path.open("rb") as audio:
                    text = self.ai_client.transcribe(audio)
                if text:
                    shared_state.session_transcripts[session_id]["transcripts"].append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"), "text": text,
                    })
                    if save_transcript_to_file(session_id) is None:
                        raise OSError("Salvataggio trascrizione fallito")
                    self.events.put(("transcribed", session_id, text))
            except Exception as exc:
                message = error_message(exc)
                shared_state.session_transcripts[session_id].setdefault("errors", []).append(message)
                self.events.put(("error", session_id, message))
                if kind == "finish":
                    self.events.put(("finished", session_id, None))
            finally:
                self.jobs.task_done()

    def stop(self):
        self.jobs.put(("shutdown", None, None, None))
