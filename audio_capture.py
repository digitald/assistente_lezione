"""Scrittura audio su un thread dedicato, con memoria limitata e coda drenata."""
import queue
import threading
import time

import soundfile as sf

from app_errors import error_message


class BufferedAudioWriter:
    def __init__(self, path, samplerate, queue_blocks=128):
        self.file = sf.SoundFile(path, mode="w", samplerate=samplerate,
                                 channels=1, subtype="PCM_16")
        self.blocks = queue.Queue(maxsize=queue_blocks)
        self.frames = 0
        self.error = ""
        self.closed = False
        self.thread = threading.Thread(target=self._write, name="audio-writer", daemon=True)
        self.thread.start()

    def submit(self, samples):
        # PortAudio riutilizza il buffer: la coda deve possederne una copia.
        # Il callback non aspetta mai il disco o spazio libero nella coda.
        if self.error or self.closed:
            return False
        try:
            self.blocks.put_nowait(samples.copy())
            return True
        except queue.Full:
            self.error = "Il disco non tiene il passo con il microfono. Ferma la registrazione; l'audio già scritto è conservato."
            return False

    def _write(self):
        failed = False
        last_flush = time.monotonic()
        try:
            while True:
                samples = self.blocks.get()
                try:
                    if samples is None:
                        break
                    if not failed:
                        self.file.write(samples)
                        self.frames += len(samples)
                        if time.monotonic() - last_flush >= 1:
                            self.file.flush()
                            last_flush = time.monotonic()
                except Exception as exc:
                    self.error = error_message(exc)
                    failed = True
                finally:
                    self.blocks.task_done()
        finally:
            try:
                self.file.close()
            except Exception as exc:
                self.error = error_message(exc)

    def close(self):
        # Chiamare solo dopo aver fermato il produttore (lo stream audio).
        if not self.closed:
            self.closed = True
            self.blocks.put(None)
            self.thread.join()
