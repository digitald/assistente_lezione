"""Verifica locale; --microfono acquisisce due secondi senza salvarli o inviarli."""
import argparse
import importlib
import sys
from version import __version__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--microfono", action="store_true")
    parser.add_argument("--desktop", action="store_true", help="Verifica anche l'interfaccia Tkinter precedente")
    args = parser.parse_args()
    print("Assistente Lezione:", __version__, "— Python:", sys.version.split()[0])
    for name in ("openai", "sounddevice", "soundfile", "numpy", "flask", "waitress", "av", "faster_whisper", "ctranslate2"):
        importlib.import_module(name)
        print(name + ": OK")
    if args.desktop:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.update()
        root.destroy()
        print("Interfaccia Tkinter: OK")
    import sounddevice as sd
    if not args.microfono:
        try:
            count = sum(device['max_input_channels'] > 0 for device in sd.query_devices())
            print("Dispositivi di ingresso:", count, "— nessuna acquisizione eseguita.")
        except sd.PortAudioError:
            print("Dispositivi audio non disponibili; l'importazione di file resta utilizzabile.")
        return
    print("Microfono predefinito:", sd.query_devices(kind="input")["name"])
    sd.check_input_settings(samplerate=16000, channels=1, dtype="float32")
    print("Formato 16 kHz mono: OK")
    if args.microfono:
        import numpy as np
        audio = sd.rec(32000, samplerate=16000, channels=1, dtype="float32")
        sd.wait()
        if audio.shape != (32000, 1) or not np.isfinite(audio).all():
            raise RuntimeError("Acquisizione audio non valida")
        print(f"Acquisizione di 2 secondi: OK; RMS={np.sqrt(np.mean(audio ** 2)):.5f}")
        print("Audio non salvato e non inviato. La qualità del parlato va verificata durante la prova reale.")


if __name__ == "__main__":
    main()
