# gui.py (Versione 2.2 - Correzione del typo)

import tkinter as tk
from tkinter import messagebox, Listbox, Scrollbar, font
import subprocess
import sys
import os
import threading
from pathlib import Path
from datetime import datetime

import config
import shared_state
from utils import generate_and_save_notes, save_transcript_to_file
from audio_worker import TranscriptionWorker
from transcribers import ApiTranscriber, LocalTranscriber

class AppGUI:
    def __init__(self, master, ai_client):
        self.master = master
        self.ai_client = ai_client
        
        self.master.title("Assistente Lezione (v2.2)")
        self.master.geometry("600x650")
        self.master.minsize(500, 600)
        
        self.displayed_session_ids = []
        self.worker_thread = None
        self.blink_job_id = None
        
        self.execution_mode = tk.StringVar(value=config.EXECUTION_MODE)
        
        self.create_widgets()
        self.refresh_sessions_list()

    def create_widgets(self):
        bold_font = font.Font(family="Helvetica", size=10, weight="bold")
        main_frame = tk.Frame(self.master, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        mode_frame = tk.LabelFrame(main_frame, text="1. Scegli Modalità di Trascrizione", padx=10, pady=10)
        mode_frame.pack(fill=tk.X, pady=5)
        
        self.mode_radio_buttons = []
        r1 = tk.Radiobutton(mode_frame, text="API OpenAI (Online, max qualità)", variable=self.execution_mode, value="API")
        r1.pack(anchor=tk.W)
        r2 = tk.Radiobutton(mode_frame, text="GPU Locale (Veloce, gratis)", variable=self.execution_mode, value="GPU")
        r2.pack(anchor=tk.W)
        r3 = tk.Radiobutton(mode_frame, text="CPU Locale (Lenta, compatibile)", variable=self.execution_mode, value="CPU")
        r3.pack(anchor=tk.W)
        self.mode_radio_buttons.extend([r1, r2, r3])

        session_frame = tk.LabelFrame(main_frame, text="2. Controllo Lezione", padx=10, pady=10)
        session_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(session_frame, text="Docente:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.docente_entry = tk.Entry(session_frame)
        self.docente_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        tk.Label(session_frame, text="Materia:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.materia_entry = tk.Entry(session_frame)
        self.materia_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
        
        # ✅ CORREZIONE 1:
        session_frame.grid_columnconfigure(1, weight=1)
        
        controls_container = tk.Frame(session_frame)
        controls_container.grid(row=2, column=0, columnspan=2, pady=(10,0), sticky='ew')
        
        # ✅ CORREZIONE 2:
        controls_container.grid_columnconfigure((0, 1, 2), weight=1)

        self.start_button = tk.Button(controls_container, text="▶ Avvia", command=self.start_session_gui, bg="#d4edda", fg="#155724", font=bold_font)
        self.start_button.grid(row=0, column=0, padx=2, sticky='ew')
        
        self.pause_button = tk.Button(controls_container, text="⏸ Pausa", command=self.toggle_pause_resume, bg="#cfe2ff", fg="#0a3678", font=bold_font, state='disabled')
        self.pause_button.grid(row=0, column=1, padx=2, sticky='ew')
        
        self.stop_button = tk.Button(controls_container, text="⏹ Ferma", command=self.stop_session_gui, bg="#f8d7da", fg="#721c24", font=bold_font, state='disabled')
        self.stop_button.grid(row=0, column=2, padx=2, sticky='ew')

        past_sessions_frame = tk.LabelFrame(main_frame, text="3. Lezioni Archiviate", padx=10, pady=10)
        past_sessions_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 5))
        
        list_frame = tk.Frame(past_sessions_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.session_listbox = Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.session_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.session_listbox.yview)

        buttons_frame = tk.Frame(past_sessions_frame)
        buttons_frame.pack(fill=tk.X, pady=5)
        tk.Button(buttons_frame, text="🔄 Ricarica Lista", command=self.refresh_sessions_list).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(buttons_frame, text="📝 Genera/Vedi Appunti", command=self.generate_notes_gui).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(buttons_frame, text="📜 Vedi Trascrizione", command=self.view_transcript_gui).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.status_label = tk.Label(self.master, text="Stato: Inattivo", fg="gray", bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=5)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Button(self.master, text="Chiudi Applicazione", command=self.shutdown_application, bg="#6c757d", fg="white").pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        self.master.protocol("WM_DELETE_WINDOW", self.shutdown_application)

    # --- Metodi di Azione (invariati, ma inclusi per completezza) ---

    def start_session_gui(self):
        if self.worker_thread is None:
            mode = self.execution_mode.get()
            transcriber = None
            try:
                if mode == "API":
                    transcriber = ApiTranscriber(self.ai_client)
                elif mode == "GPU":
                    transcriber = LocalTranscriber(model_size=config.LOCAL_MODEL_SIZE, device="cuda")
                elif mode == "CPU":
                    transcriber = LocalTranscriber(model_size=config.LOCAL_MODEL_SIZE, device="cpu")
            except Exception as e:
                messagebox.showerror("Errore Avvio Worker", f"Impossibile inizializzare il motore '{mode}'.\n\n{e}")
                return

            worker = TranscriptionWorker(transcriber)
            self.worker_thread = threading.Thread(target=worker.run, daemon=True)
            self.worker_thread.start()
            for btn in self.mode_radio_buttons: btn.config(state='disabled')

        docente = self.docente_entry.get().strip()
        materia = self.materia_entry.get().strip()
        if not docente or not materia:
            messagebox.showerror("Dati Mancanti", "I campi 'Docente' e 'Materia' non possono essere vuoti.")
            return

        docente_safe = docente.replace(" ", "_"); materia_safe = materia.replace(" ", "_")
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M")
        session_id = f"{docente_safe}_{materia_safe}_{timestamp}"
        
        shared_state.current_session_id = session_id
        shared_state.session_transcripts[session_id] = {"docente": docente, "materia": materia, "start_time": now.isoformat(), "transcripts": []}
        shared_state.session_active = True
        shared_state.session_paused = False

        self.status_label.config(text=f"REC ● In Registrazione", font=font.Font(weight="bold"))
        self.blink_status()
        
        self.docente_entry.config(state='disabled')
        self.materia_entry.config(state='disabled')
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.pause_button.config(state='normal')
        print(f"▶️ Sessione avviata: {session_id}")
    
    def stop_session_gui(self):
        if not shared_state.session_active: return
        if self.blink_job_id:
            self.master.after_cancel(self.blink_job_id)
            self.blink_job_id = None

        session_id = shared_state.current_session_id
        print(f"⏹️  Sessione fermata: {session_id}")
        save_transcript_to_file(session_id)
        
        shared_state.session_active = False
        shared_state.session_paused = False
        shared_state.current_session_id = None
        
        self.status_label.config(text="Stato: Inattivo", font=font.Font(), background=self.master.cget('bg'), fg='gray')
        self.docente_entry.config(state='normal')
        self.materia_entry.config(state='normal')
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.pause_button.config(state='disabled', text="⏸ Pausa")
        self.refresh_sessions_list()

    def toggle_pause_resume(self):
        if not shared_state.session_active: return
        shared_state.session_paused = not shared_state.session_paused
        if shared_state.session_paused:
            self.pause_button.config(text="▶ Riprendi", bg="#fff3cd", fg="#664d03")
            self.status_label.config(text="Stato: PAUSA", font=font.Font(weight="bold"), background="#ffc107", foreground="black")
            if self.blink_job_id: self.master.after_cancel(self.blink_job_id)
        else:
            self.pause_button.config(text="⏸ Pausa", bg="#cfe2ff", fg="#0a3678")
            self.status_label.config(text=f"REC ● In Registrazione", font=font.Font(weight="bold"))
            self.blink_status()

    def blink_status(self):
        if shared_state.session_paused: return
        current_color = self.status_label.cget("background")
        next_color = "red" if current_color != "red" else "#f8d7da"
        self.status_label.config(background=next_color, foreground="white" if next_color == "red" else "black")
        self.blink_job_id = self.master.after(700, self.blink_status)
    
    def refresh_sessions_list(self):
        self.session_listbox.delete(0, tk.END)
        self.displayed_session_ids.clear()
        all_session_ids = set()
        for f in Path(config.TRANSCRIPTS_DIR).glob("trascrizione_*.txt"): all_session_ids.add(f.stem.replace("trascrizione_", ""))
        for f in Path(config.NOTES_DIR).glob("appunti_*.txt"): all_session_ids.add(f.stem.replace("appunti_", ""))
        sorted_ids = sorted(list(all_session_ids), key=lambda x: x.split('_')[-2] + x.split('_')[-1], reverse=True)
        self.displayed_session_ids.extend(sorted_ids)
        for session_id in sorted_ids:
            transcript_exists = (Path(config.TRANSCRIPTS_DIR) / f"trascrizione_{session_id}.txt").exists()
            notes_exist = (Path(config.NOTES_DIR) / f"appunti_{session_id}.txt").exists()
            transcript_icon = "📜" if transcript_exists else "⏳"; notes_icon = "📝" if notes_exist else "▪️"
            parts = session_id.split('_'); docente, materia = parts[0], " ".join(parts[1:-2]); data_str, ora_str = parts[-2], parts[-1]
            display_text = f'{transcript_icon}{notes_icon} {materia} - {docente} ({data_str[6:8]}/{data_str[4:6]} {ora_str[0:2]}:{ora_str[2:4]})'
            self.session_listbox.insert(tk.END, display_text)

    def get_selected_session_id(self):
        selected_indices = self.session_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Nessuna Selezione", "Per favore, seleziona una sessione dalla lista.")
            return None
        return self.displayed_session_ids[selected_indices[0]]

    def generate_notes_gui(self):
        session_id = self.get_selected_session_id()
        if not session_id: return
        notes_filepath = Path(config.NOTES_DIR) / f"appunti_{session_id}.txt"
        if not notes_filepath.exists():
            if not messagebox.askyesno("Conferma", "Appunti non trovati. Generarli ora?"): return
            self.status_label.config(text=f"Stato: Genero appunti...", fg="orange")
            self.master.update_idletasks()
            def run_generation():
                success = generate_and_save_notes(session_id, self.ai_client)
                if success:
                    self.status_label.config(text="Stato: Appunti generati!", fg="blue")
                    self.open_file(notes_filepath)
                else:
                    self.status_label.config(text="Stato: Errore generazione", fg="red")
                    messagebox.showerror("Errore", "Impossibile generare gli appunti.")
            threading.Thread(target=run_generation, daemon=True).start()
        else:
            self.open_file(notes_filepath)

    def view_transcript_gui(self):
        session_id = self.get_selected_session_id()
        if not session_id: return
        filepath = Path(config.TRANSCRIPTS_DIR) / f"trascrizione_{session_id}.txt"
        if filepath.exists(): self.open_file(filepath)
        else: messagebox.showerror("Errore", "File trascrizione non trovato.")
    
    def open_file(self, filepath):
        try:
            if sys.platform == "win32": os.startfile(filepath)
            elif sys.platform == "darwin": subprocess.run(["open", filepath], check=True)
            else: subprocess.run(["xdg-open", filepath], check=True)
        except Exception as e: messagebox.showerror("Errore Apertura File", f"Impossibile aprire il file:\n{e}")

    def shutdown_application(self):
        if messagebox.askyesno("Conferma Uscita", "Sei sicuro di voler chiudere l'applicazione?"):
            print("🛑 Chiusura dell'applicazione...")
            self.master.destroy()
            os._exit(0)

# La funzione di avvio, che crea l'istanza della classe
def launch_gui(ai_client):
    root = tk.Tk()
    app = AppGUI(root, ai_client)
    root.mainloop()