# gui.py (versione finale per Assistente Lezione)

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

# in gui.py

# ... (tutte le importazioni esistenti) ...

# gui.py (Versione 1.1 con Pausa/Riprendi)

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

def launch_gui(ai_client):
    root = tk.Tk()
    root.title("Assistente Lezione (v1.1)")
    root.geometry("600x600")
    root.minsize(500, 500)

    # Variabili di stato della GUI
    displayed_session_ids = []
    blink_job_id = None

    # --- Funzioni Logiche della GUI ---

    def toggle_pause_resume():
        if not shared_state.session_active: return

        shared_state.session_paused = not shared_state.session_paused

        if shared_state.session_paused:
            pause_button.config(text="▶ Riprendi", bg="#fff3cd", fg="#664d03")
            status_label.config(text="Stato: PAUSA", font=bold_font, background="#ffc107", foreground="black")
            # Ferma il lampeggio
            if blink_job_id:
                root.after_cancel(blink_job_id)
        else: # Riprendi
            pause_button.config(text="⏸ Pausa", bg="#cfe2ff", fg="#0a3678")
            status_label.config(text=f"REC ● {shared_state.current_session_id}", font=bold_font)
            blink_status() # Fa ripartire il lampeggio

    def blink_status():
        nonlocal blink_job_id
        if shared_state.session_paused: return # Non lampeggiare se in pausa
        
        current_color = status_label.cget("background")
        next_color = "red" if current_color != "red" else "#f8d7da"
        status_label.config(background=next_color, foreground="white" if next_color == "red" else "black")
        blink_job_id = root.after(700, blink_status)

    def start_session_gui():
        docente = docente_entry.get().strip()
        materia = materia_entry.get().strip()
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

        status_label.config(text=f"REC ● {session_id}", font=bold_font)
        blink_status()
        
        docente_entry.config(state='disabled')
        materia_entry.config(state='disabled')
        start_button.config(state='disabled')
        stop_button.config(state='normal')
        pause_button.config(state='normal')
        print(f"▶️ Sessione avviata: {session_id}")

    def stop_session_gui():
        if not shared_state.session_active: return
        nonlocal blink_job_id
        if blink_job_id:
            root.after_cancel(blink_job_id)
            blink_job_id = None

        session_id = shared_state.current_session_id
        print(f"⏹️  Sessione fermata: {session_id}")
        save_transcript_to_file(session_id)
        
        shared_state.session_active = False
        shared_state.session_paused = False
        shared_state.current_session_id = None
        
        status_label.config(text="Stato: Inattivo", font=font.Font(), background=root.cget('bg'), fg='gray')
        docente_entry.config(state='normal')
        materia_entry.config(state='normal')
        start_button.config(state='normal')
        stop_button.config(state='disabled')
        pause_button.config(state='disabled', text="⏸ Pausa")
        refresh_sessions_list()
    
    def refresh_sessions_list():
        nonlocal displayed_session_ids
        session_listbox.delete(0, tk.END)
        displayed_session_ids.clear()
        all_session_ids = set()
        for f in Path(config.TRANSCRIPTS_DIR).glob("trascrizione_*.txt"):
            all_session_ids.add(f.stem.replace("trascrizione_", ""))
        for f in Path(config.NOTES_DIR).glob("appunti_*.txt"):
            all_session_ids.add(f.stem.replace("appunti_", ""))
        sorted_ids = sorted(list(all_session_ids), key=lambda x: x.split('_')[-2] + x.split('_')[-1], reverse=True)
        displayed_session_ids.extend(sorted_ids)
        for session_id in sorted_ids:
            transcript_exists = (Path(config.TRANSCRIPTS_DIR) / f"trascrizione_{session_id}.txt").exists()
            notes_exist = (Path(config.NOTES_DIR) / f"appunti_{session_id}.txt").exists()
            transcript_icon = "📜" if transcript_exists else "⏳"
            notes_icon = "📝" if notes_exist else "▪️"
            parts = session_id.split('_')
            docente, materia = parts[0], " ".join(parts[1:-2])
            data_str, ora_str = parts[-2], parts[-1]
            display_text = f'{transcript_icon}{notes_icon} {materia} - {docente} ({data_str[6:8]}/{data_str[4:6]} {ora_str[0:2]}:{ora_str[2:4]})'
            session_listbox.insert(tk.END, display_text)

    def get_selected_session_id():
        selected_indices = session_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Nessuna Selezione", "Per favore, seleziona una sessione dalla lista.")
            return None
        return displayed_session_ids[selected_indices[0]]

    def generate_notes_gui():
        session_id = get_selected_session_id()
        if not session_id: return
        notes_filepath = Path(config.NOTES_DIR) / f"appunti_{session_id}.txt"
        if not notes_filepath.exists():
            if not messagebox.askyesno("Conferma", "Appunti non trovati. Generarli ora?"): return
            status_label.config(text=f"Stato: Genero appunti...", fg="orange")
            root.update_idletasks()
            def run_generation():
                success = generate_and_save_notes(session_id, ai_client)
                if success:
                    status_label.config(text="Stato: Appunti generati!", fg="blue")
                    open_file(notes_filepath)
                else:
                    status_label.config(text="Stato: Errore generazione", fg="red")
                    messagebox.showerror("Errore", "Impossibile generare gli appunti.")
            threading.Thread(target=run_generation, daemon=True).start()
        else:
            open_file(notes_filepath)

    def view_transcript_gui():
        session_id = get_selected_session_id()
        if not session_id: return
        filepath = Path(config.TRANSCRIPTS_DIR) / f"trascrizione_{session_id}.txt"
        if filepath.exists(): open_file(filepath)
        else: messagebox.showerror("Errore", "File trascrizione non trovato.")

    def open_file(filepath):
        try:
            if sys.platform == "win32": os.startfile(filepath)
            elif sys.platform == "darwin": subprocess.run(["open", filepath], check=True)
            else: subprocess.run(["xdg-open", filepath], check=True)
        except Exception as e: messagebox.showerror("Errore Apertura File", f"Impossibile aprire il file:\n{e}")

    def shutdown_application():
        if messagebox.askyesno("Conferma Uscita", "Sei sicuro di voler chiudere l'applicazione?"):
            print("🛑 Chiusura dell'applicazione...")
            root.destroy()
            os._exit(0)
    
    # --- Struttura Grafica della GUI ---
    bold_font = font.Font(family="Helvetica", size=10, weight="bold")
    main_frame = tk.Frame(root, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    session_frame = tk.LabelFrame(main_frame, text="Controllo Lezione", padx=10, pady=10)
    session_frame.pack(fill=tk.X, pady=5)
    
    tk.Label(session_frame, text="Docente:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
    docente_entry = tk.Entry(session_frame)
    docente_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
    tk.Label(session_frame, text="Materia:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
    materia_entry = tk.Entry(session_frame)
    materia_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=2)
    
    controls_container = tk.Frame(session_frame)
    controls_container.grid(row=2, column=0, columnspan=2, pady=(10,0), sticky='ew')
    controls_container.grid_columnconfigure((0, 1, 2), weight=1)

    start_button = tk.Button(controls_container, text="▶ Avvia", command=start_session_gui, bg="#d4edda", fg="#155724", font=bold_font)
    start_button.grid(row=0, column=0, padx=2, sticky='ew')
    
    pause_button = tk.Button(controls_container, text="⏸ Pausa", command=toggle_pause_resume, bg="#cfe2ff", fg="#0a3678", font=bold_font, state='disabled')
    pause_button.grid(row=0, column=1, padx=2, sticky='ew')
    
    stop_button = tk.Button(controls_container, text="⏹ Ferma", command=stop_session_gui, bg="#f8d7da", fg="#721c24", font=bold_font, state='disabled')
    stop_button.grid(row=0, column=2, padx=2, sticky='ew')
    
    session_frame.grid_columnconfigure(1, weight=1)

    past_sessions_frame = tk.LabelFrame(main_frame, text="Lezioni Archiviate", padx=10, pady=10)
    past_sessions_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 5))
    
    list_frame = tk.Frame(past_sessions_frame)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    scrollbar = Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    session_listbox = Listbox(list_frame, yscrollcommand=scrollbar.set)
    session_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=session_listbox.yview)

    buttons_frame = tk.Frame(past_sessions_frame)
    buttons_frame.pack(fill=tk.X, pady=5)
    tk.Button(buttons_frame, text="🔄 Ricarica Lista", command=refresh_sessions_list).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
    tk.Button(buttons_frame, text="📝 Genera/Vedi Appunti", command=generate_notes_gui).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
    tk.Button(buttons_frame, text="📜 Vedi Trascrizione", command=view_transcript_gui).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
    
    status_label = tk.Label(root, text="Stato: Inattivo", fg="gray", bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=5)
    status_label.pack(side=tk.BOTTOM, fill=tk.X)
    tk.Button(root, text="Chiudi Applicazione", command=shutdown_application, bg="#6c757d", fg="white").pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

    root.protocol("WM_DELETE_WINDOW", shutdown_application)
    
    refresh_sessions_list()
    root.mainloop()