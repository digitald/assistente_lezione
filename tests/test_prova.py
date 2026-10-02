import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main  # Installa anche il fallback di configurazione, se necessario.
import config
import shared_state
from demo_client import DemoAIClient
from gui import launch_gui
from utils import generate_and_save_notes


class DemoFlowTest(unittest.TestCase):
    def test_gui_session_pause_save_and_notes(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(config, "TRANSCRIPTS_DIR", folder), patch.object(config, "NOTES_DIR", folder):
                shared_state.session_transcripts.clear()
                shared_state.session_active = False
                shared_state.session_paused = False
                shared_state.current_session_id = None
                original_mainloop = tk.Tk.mainloop
                failures = []

                def drive(root, *args, **kwargs):
                    root.withdraw()
                    def callback_error(exc_type, exc, traceback):
                        failures.append(exc)
                        root.destroy()
                    root.report_callback_exception = callback_error
                    def walk(widget):
                        for child in widget.winfo_children():
                            yield child
                            yield from walk(child)
                    widgets = list(walk(root))
                    buttons = {w.cget("text"): w for w in widgets if isinstance(w, tk.Button)}
                    session_id = None

                    def start_pause_resume_stop():
                        nonlocal session_id
                        buttons["▶ Avvia"].invoke()
                        session_id = shared_state.current_session_id
                        self.assertEqual(len(shared_state.session_transcripts[session_id]["transcripts"]), 1)
                        buttons["⏸ Pausa"].invoke()
                        self.assertTrue(shared_state.session_paused)
                        buttons["⏸ Pausa"].invoke()
                        self.assertFalse(shared_state.session_paused)
                        buttons["⏹ Ferma"].invoke()
                        self.assertFalse(shared_state.session_active)
                        transcript = Path(folder) / f"trascrizione_{session_id}.txt"
                        self.assertIn("PROVA SIMULATA", transcript.read_text(encoding="utf-8"))
                        listbox = next(w for w in widgets if isinstance(w, tk.Listbox))
                        self.assertEqual(listbox.size(), 1)
                        listbox.selection_set(0)
                        buttons["📝 Genera/Vedi Appunti"].invoke()

                    def finish():
                        notes = Path(folder) / f"appunti_{session_id}.txt"
                        self.assertIn("Nessuna elaborazione AI", notes.read_text(encoding="utf-8"))
                        root.destroy()

                    def guard(fn):
                        def run():
                            try:
                                fn()
                            except Exception as exc:
                                failures.append(exc)
                                root.destroy()
                        return run
                    root.after(10, guard(start_pause_resume_stop))
                    root.after(700, guard(finish))
                    original_mainloop(root, *args, **kwargs)

                with patch.object(tk.Tk, "mainloop", drive), patch("gui.messagebox.askyesno", return_value=True), patch("gui.os.startfile"):
                    launch_gui(DemoAIClient(), demo=True)
                if failures:
                    raise failures[0]

    def test_empty_transcript_has_no_notes(self):
        self.assertEqual(DemoAIClient().summarize_transcript("  "), "")

    def test_reopens_transcript_from_disk_in_app(self):
        from tkinter.scrolledtext import ScrolledText
        with tempfile.TemporaryDirectory() as folder, patch.object(config, "TRANSCRIPTS_DIR", folder), patch.object(config, "NOTES_DIR", folder):
            saved = Path(folder) / "trascrizione_Docente_Materia_20261002_120000.txt"
            saved.write_text("Testo salvato in una sessione precedente", encoding="utf-8")
            def inspect(root, *args, **kwargs):
                root.withdraw()
                def walk(widget):
                    for child in widget.winfo_children():
                        yield child
                        yield from walk(child)
                widgets = list(walk(root))
                listbox = next(w for w in widgets if isinstance(w, tk.Listbox))
                self.assertEqual(listbox.size(), 1)
                listbox.selection_set(0)
                next(w for w in widgets if isinstance(w, tk.Button) and w.cget("text") == "📜 Vedi Trascrizione").invoke()
                viewer = next(w for w in walk(root) if isinstance(w, ScrolledText))
                self.assertIn("sessione precedente", viewer.get("1.0", tk.END))
                root.destroy()
            with patch.object(tk.Tk, "mainloop", inspect):
                launch_gui(DemoAIClient(), demo=True)

    def test_real_gui_waits_for_final_transcription(self):
        import time
        import numpy as np
        from audio_worker import TranscriptionWorker
        from unittest.mock import MagicMock
        class Client:
            def transcribe(self, audio):
                time.sleep(0.2)
                return "ultimo tratto della registrazione"
        with tempfile.TemporaryDirectory() as folder, patch.object(config, "TRANSCRIPTS_DIR", folder), patch.object(config, "NOTES_DIR", folder), patch("audio_worker.sd.InputStream", return_value=MagicMock()):
            worker = TranscriptionWorker(Client())
            worker.start()
            failures = []
            original_mainloop = tk.Tk.mainloop
            def drive(root, *args, **kwargs):
                root.withdraw()
                def walk(widget):
                    for child in widget.winfo_children():
                        yield child
                        yield from walk(child)
                widgets = list(walk(root))
                buttons = {w.cget("text"): w for w in widgets if isinstance(w, tk.Button)}
                for entry in (w for w in widgets if isinstance(w, tk.Entry)):
                    entry.insert(0, "Test")
                session_id = None
                def begin():
                    nonlocal session_id
                    buttons["▶ Avvia"].invoke()
                    session_id = shared_state.current_session_id
                    data = np.ones((1000, 1), dtype=np.float32) * 0.002
                    worker.audio_callback(data, len(data), None, None)
                    buttons["⏹ Ferma"].invoke()
                    self.assertEqual(buttons["▶ Avvia"].cget("state"), "disabled")
                    self.assertEqual(shared_state.current_session_id, session_id)
                def finish():
                    self.assertIsNone(shared_state.current_session_id)
                    self.assertEqual(buttons["▶ Avvia"].cget("state"), "normal")
                    text = (Path(folder) / f"trascrizione_{session_id}.txt").read_text(encoding="utf-8")
                    self.assertIn("ultimo tratto", text)
                    root.destroy()
                def guarded(fn):
                    def run():
                        try:
                            fn()
                        except Exception as exc:
                            failures.append(exc)
                            root.destroy()
                    return run
                root.after(10, guarded(begin))
                root.after(700, guarded(finish))
                original_mainloop(root, *args, **kwargs)
            try:
                with patch.object(tk.Tk, "mainloop", drive):
                    launch_gui(Client(), worker=worker)
                if failures:
                    raise failures[0]
            finally:
                worker.stop()
                worker.join(2)

    def test_missing_transcript_does_not_create_notes(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(config, "TRANSCRIPTS_DIR", folder):
            self.assertFalse(generate_and_save_notes("missing", DemoAIClient()))


if __name__ == "__main__":
    unittest.main()
