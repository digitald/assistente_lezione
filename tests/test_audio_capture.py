import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf

from audio_capture import BufferedAudioWriter


class AudioCaptureTests(unittest.TestCase):
    def test_copies_input_and_drains_tail_before_close(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'audio.wav'
            writer = BufferedAudioWriter(path, 16000)
            samples = np.full(1024, 0.25, dtype=np.float32)
            for _ in range(20):
                self.assertTrue(writer.submit(samples))
            samples[:] = 0
            writer.close()
            writer.close()
            audio, rate = sf.read(path)
            self.assertEqual(rate, 16000)
            self.assertEqual(len(audio), 20 * 1024)
            self.assertTrue(np.allclose(audio, 0.25))
            self.assertFalse(writer.thread.is_alive())
            self.assertFalse(writer.submit(samples))

    def test_slow_disk_has_bounded_queue_and_reports_overflow(self):
        entered, release = threading.Event(), threading.Event()
        with patch('audio_capture.sf.SoundFile') as sound_file:
            def slow_write(samples):
                entered.set()
                release.wait(5)
            sound_file.return_value.write.side_effect = slow_write
            writer = BufferedAudioWriter('unused', 16000, queue_blocks=1)
            try:
                self.assertTrue(writer.submit(np.zeros(16)))
                self.assertTrue(entered.wait(2))
                self.assertTrue(writer.submit(np.zeros(16)))
                self.assertFalse(writer.submit(np.zeros(16)))
                self.assertIn('disco', writer.error)
                self.assertEqual(writer.blocks.qsize(), 1)
            finally:
                release.set()
                writer.close()
            self.assertEqual(writer.frames, 32)

    def test_disk_error_closes_writer_without_deadlock(self):
        with patch('audio_capture.sf.SoundFile') as sound_file:
            sound_file.return_value.write.side_effect = OSError('Disk full')
            writer = BufferedAudioWriter('unused', 16000)
            writer.submit(np.zeros(16))
            writer.close()
            self.assertTrue(writer.error)
            self.assertEqual(writer.frames, 0)
            self.assertFalse(writer.thread.is_alive())
            sound_file.return_value.close.assert_called_once()
