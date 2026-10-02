import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main
import config
import shared_state
import numpy as np
import soundfile as sf
from audio_worker import TranscriptionWorker


class WorkerTests(unittest.TestCase):
    def setUp(self):
        shared_state.session_transcripts.clear()
        shared_state.session_active = True
        shared_state.session_paused = False
        shared_state.current_session_id = "A"
        shared_state.session_transcripts["A"] = {"transcripts": []}

    def test_consumes_once_keeps_quiet_voice_tail_and_pause(self):
        lengths = []
        class Client:
            def transcribe(self, audio):
                data, rate = sf.read(audio)
                lengths.append(len(data))
                return f"blocco {len(lengths)}"
        with tempfile.TemporaryDirectory() as folder, patch.object(config, "TRANSCRIPTS_DIR", folder), patch("audio_worker.sd.InputStream", return_value=MagicMock()):
            worker = TranscriptionWorker(Client(), chunk_duration=1)
            worker.start()
            worker.begin_session("A")
            quiet = np.ones((40000, 1), dtype=np.float32) * 0.002
            worker.audio_callback(quiet, len(quiet), None, None)
            shared_state.session_paused = True
            worker.audio_callback(quiet, len(quiet), None, None)
            shared_state.session_active = False
            worker.finish_session()
            worker.jobs.join()
            worker.stop()
            worker.join(2)
            self.assertEqual(lengths, [16000, 16000, 8000])
            full_audio, rate = sf.read(Path(folder) / "audio" / "audio_A.wav")
            self.assertEqual(len(full_audio), 40000)
            text = (Path(folder) / "trascrizione_A.txt").read_text(encoding="utf-8")
            self.assertEqual(text.count("blocco"), 3)
            self.assertIn("blocco 3", text)

    def test_late_result_stays_with_original_session(self):
        entered = threading.Event()
        release = threading.Event()
        class Client:
            def transcribe(self, audio):
                entered.set()
                release.wait(3)
                return "risposta tardiva"
        with tempfile.TemporaryDirectory() as folder, patch.object(config, "TRANSCRIPTS_DIR", folder), patch("audio_worker.sd.InputStream", return_value=MagicMock()):
            worker = TranscriptionWorker(Client(), chunk_duration=1)
            worker.start()
            worker.begin_session("A")
            data = np.ones((16000, 1), dtype=np.float32) * 0.01
            worker.audio_callback(data, len(data), None, None)
            self.assertTrue(entered.wait(2))
            shared_state.session_active = False
            worker.finish_session()
            self.assertFalse((Path(folder) / "trascrizione_A.txt").exists())
            shared_state.current_session_id = "B"
            shared_state.session_transcripts["B"] = {"transcripts": []}
            release.set()
            worker.jobs.join()
            worker.stop()
            worker.join(2)
            self.assertEqual(shared_state.session_transcripts["B"]["transcripts"], [])
            self.assertIn("risposta tardiva", (Path(folder) / "trascrizione_A.txt").read_text(encoding="utf-8"))

    def test_api_error_preserves_audio_and_exposes_error(self):
        class AuthenticationError(Exception):
            status_code = 401
        class Client:
            def transcribe(self, audio):
                raise AuthenticationError()
        with tempfile.TemporaryDirectory() as folder, patch.object(config, "TRANSCRIPTS_DIR", folder), patch("audio_worker.sd.InputStream", return_value=MagicMock()):
            worker = TranscriptionWorker(Client())
            worker.start()
            worker.begin_session("A")
            data = np.ones((1000, 1), dtype=np.float32) * 0.01
            worker.audio_callback(data, len(data), None, None)
            shared_state.session_active = False
            worker.finish_session()
            worker.jobs.join()
            worker.stop()
            worker.join(2)
            self.assertTrue((Path(folder) / "audio" / "audio_A.wav").exists())
            self.assertTrue((Path(folder) / "audio" / "A" / "segmento_000000.wav").exists())
            self.assertEqual((Path(folder) / "trascrizione_A.txt").read_text(), "")
            self.assertIn("Chiave API non valida", shared_state.session_transcripts["A"]["errors"][0])


if __name__ == "__main__":
    unittest.main()
