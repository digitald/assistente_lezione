# audio_worker.py (versione pulita)

import threading
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
import io
from datetime import datetime

import shared_state
from ai_client import AIClient

# La classe CircularBuffer rimane invariata
class CircularBuffer:
    def __init__(self, size):
        self.buffer = np.zeros(size, dtype=np.float32)
        self.size = size
        self.index = 0
        self.filled = False
        
    def add_data(self, data):
        data_len = len(data)
        if data_len > self.size:
            data = data[-self.size:]
        if self.index + data_len > self.size:
            part1 = self.size - self.index
            self.buffer[self.index:self.index+part1] = data[:part1]
            self.buffer[0:data_len-part1] = data[part1:]
            self.index = data_len - part1
        else:
            self.buffer[self.index:self.index+data_len] = data
            self.index = (self.index + data_len) % self.size
        if not self.filled and self.index == 0:
            self.filled = True
            
    def get_data(self):
        if self.filled:
            return np.concatenate([self.buffer[self.index:], self.buffer[:self.index]])
        return self.buffer[:self.index]


class TranscriptionWorker(threading.Thread):
    def __init__(self, transcriber_engine, chunk_duration=4, sample_rate=16000):
        super().__init__(daemon=True)
        self.transcriber_engine = transcriber_engine
        self.chunk_duration = chunk_duration
        self.sample_rate = sample_rate
        self.samples_per_chunk = int(sample_rate * chunk_duration)
        self.running = False
        self.processing = False
        self.audio_buffer = CircularBuffer(sample_rate * (chunk_duration * 3))
        self.lock = threading.Lock()

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"Audio status: {status}")
        if self.running and shared_state.session_active and not shared_state.session_paused:
            with self.lock:
                self.audio_buffer.add_data(indata[:, 0])

    def run(self):
        self.running = True
        print("▶️ Worker di trascrizione avviato e in attesa di una sessione...")
        with sd.InputStream(
            samplerate=self.sample_rate, channels=1, dtype="float32",
            callback=self.audio_callback, blocksize=self.sample_rate
        ):
            while self.running:
                if not shared_state.session_active or shared_state.session_paused or self.processing:
                    time.sleep(0.1)
                    continue

                with self.lock:
                    buffered_data = self.audio_buffer.get_data()

                if len(buffered_data) >= self.samples_per_chunk:
                    self.processing = True
                    audio_chunk = buffered_data[-self.samples_per_chunk:]
                    threading.Thread(target=self.process_chunk, args=(audio_chunk,)).start()
                else:
                    time.sleep(0.1) # Breve attesa se il buffer non è ancora pieno
    
    def process_chunk(self, audio_data):
        try:
            # Calcola il volume e salta i chunk silenziosi
            rms = np.sqrt(np.mean(audio_data**2))
            if rms < 0.01:   ### era 0.01
                return

            print("🎤 Chunk audio acquisito, avvio trascrizione...")
            
            text = self.transcriber_engine.transcribe(audio_data, self.sample_rate)
            
            if text:
                print(f"📥 Trascritto: {text}")
                if shared_state.current_session_id in shared_state.session_transcripts:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    shared_state.session_transcripts[shared_state.current_session_id]["transcripts"].append({
                        "timestamp": timestamp,
                        "text": text
                    })

        except Exception as e:
            print(f"❌ Errore durante l'elaborazione del chunk: {e}")
        finally:
            self.processing = False

    def stop(self):
        self.running = False