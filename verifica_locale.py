"""Diagnostica CPU/GPU e prova locale separata dall'archivio, senza API cloud."""
import argparse
import json
import sys
import time
import tempfile
from pathlib import Path

from local_runtime import LOCAL_MODELS, LocalRuntime, load_local_model
from transcript_tools import readable_text
from audio_processing import normalize_audio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=LOCAL_MODELS, default='base')
    parser.add_argument('--audio', type=Path, help='Audio da trascrivere; senza questo argomento esegue solo la diagnosi.')
    parser.add_argument('--device', choices=('cpu', 'cuda'))
    parser.add_argument('--compute-type')
    parser.add_argument('--threads', type=int)
    parser.add_argument('--download', action='store_true', help='Consente il download del modello mancante.')
    parser.add_argument('--output-dir', type=Path, default=Path('data/validation'))
    args = parser.parse_args()
    try:
        import config
    except ModuleNotFoundError:
        import config_template as config
    import ctranslate2
    settings = LocalRuntime.from_config(config)
    device = args.device or settings.device
    settings = LocalRuntime(device, args.compute_type or
                            (settings.compute_type if device == settings.device else ('int8' if device == 'cpu' else 'float16')),
                            args.threads if args.threads is not None else settings.cpu_threads, settings.device_index)
    root = Path(__file__).resolve().parent
    print('Configurazione:', json.dumps(settings.public()))
    print('CTranslate2:', ctranslate2.__version__)
    print('GPU rilevate:', ctranslate2.get_cuda_device_count())
    settings.model_options(root / 'data/models')
    print('Dispositivo e precisione: compatibili. Questo controllo non prova ancora caricamento e inferenza.')
    if not args.audio:
        print('Per provare anche modello e librerie: aggiungi --audio FILE e, al primo uso, --download.')
        return
    if not args.audio.is_file():
        raise ValueError('Il file audio non esiste.')
    load_start = time.perf_counter()
    model = load_local_model(args.model, root / 'data/models', settings, allow_download=args.download)
    load_seconds = time.perf_counter() - load_start
    import soundfile as sf
    with tempfile.TemporaryDirectory(prefix='whisper-check-') as folder:
        normalized = Path(folder) / 'normalized.wav'
        start = time.perf_counter()
        normalize_audio(args.audio, normalized)
        normalization_seconds = time.perf_counter() - start
        result = []
        start = time.perf_counter()
        with sf.SoundFile(normalized) as audio:
            duration = len(audio) / audio.samplerate
            while True:
                waveform = audio.read(16000 * 120, dtype='float32')
                if not len(waveform):
                    break
                segments, _ = model.transcribe(waveform, language='it', vad_filter=True, beam_size=5)
                result.extend(segment.text.strip() for segment in segments)
        seconds = time.perf_counter() - start
    text = readable_text(' '.join(result))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f'locale-{args.model}-{time.time_ns()}'
    text_file = args.output_dir / (stem + '.txt')
    text_file.write_text(text + '\n', encoding='utf-8')
    report = dict(model=args.model, runtime=settings.public(), audio_file=str(args.audio.resolve()),
                  duration_seconds=duration, load_seconds=round(load_seconds, 3),
                  normalization_seconds=round(normalization_seconds, 3),
                  transcription_seconds=round(seconds, 3),
                  realtime_factor=round(seconds / duration, 3) if duration else None,
                  text_file=str(text_file), characters=len(text))
    report_file = args.output_dir / (stem + '.json')
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Verifica non riuscita: {exc}', file=sys.stderr)
        print('Per CUDA controlla driver NVIDIA, CUDA 12/cuBLAS, cuDNN 9 e PATH. Nessuna modifica alle lezioni.', file=sys.stderr)
        sys.exit(1)
