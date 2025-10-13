# transcribers.py

from faster_whisper import WhisperModel
import io
import soundfile as sf

class ApiTranscriber:
    def __init__(self, ai_client):
        self.ai_client = ai_client
        print("🎙️ Motore di trascrizione impostato su: API OpenAI")

    def transcribe(self, audio_data, sample_rate):
        wav_bytes = io.BytesIO()
        sf.write(wav_bytes, audio_data, sample_rate, format='WAV')
        wav_bytes.seek(0)
        wav_bytes.name = "stream.wav"
        return self.ai_client.transcribe(wav_bytes)

class LocalTranscriber:
    def __init__(self, model_size="base", device="cpu"):
        print(f"🎙️ Motore di trascrizione impostato su: Locale ({device})")
        print(f"⏳ Caricamento del modello '{model_size}' in memoria... (potrebbe richiedere un po' di tempo)")
        
        compute_type = "float32" if device == "cuda" else "int8"
        
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print("✅ Modello caricato.")

    def transcribe(self, audio_data, sample_rate):
        segments, _ = self.model.transcribe(
            audio_data,
            beam_size=5,
            language="it" # <-- AGGIUNGI QUESTA RIGA
        )
        text = " ".join([seg.text for seg in segments])
        return text.strip()

