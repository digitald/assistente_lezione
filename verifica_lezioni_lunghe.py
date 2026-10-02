"""Collaudo locale di file lunghi; le risposte OpenAI sono simulate, senza costi.

Non misura qualità del riconoscimento, latenza remota o ore di microfono reale.
I file audio temporanei vengono rimossi dopo ogni prova.
"""
import json
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import soundfile as sf

from lesson_service import LessonService


def check(hours):
    parent = Path(__file__).resolve().parent / 'data' / 'validation'
    parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='long-audio-', dir=parent) as directory:
        calls = []

        def transcribe(**params):
            info = sf.info(params['file'].name)
            assert info.duration <= 120
            assert Path(params['file'].name).stat().st_size < 25_000_000
            calls.append(info.frames)
            return SimpleNamespace(text=f'Parte simulata {len(calls)}')

        client = SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=transcribe)))
        service = LessonService(directory, api_key='test', client_factory=lambda: client)
        try:
            lesson = service.create({'title':f'Collaudo {hours} ore', 'engine':'openai'})
            folder = service.root / lesson['id']
            # Tono, con silenzio periodico, per esercitare anche il taglio vicino alle pause.
            second = (np.sin(np.arange(16000) * 2 * np.pi * 440 / 16000) * 0.02).astype('float32')
            with sf.SoundFile(folder / 'recording.wav', mode='w', samplerate=16000,
                              channels=1, subtype='PCM_16') as audio:
                for index in range(hours * 3600):
                    audio.write(np.zeros(16000, dtype='float32') if index % 117 == 116 else second)
            service.update(lesson['id'], audio='recording.wav')
            service.enqueue(lesson['id'], 'transcribe')
            service.jobs.join()
            result = service.get(lesson['id'])
            assert result['status'] == 'ready', result['error']
            position = 0
            for segment in result['segments']:
                assert round(segment['start'] * 16000) == position
                frames = sf.info(folder / segment['file']).frames
                assert round(segment['duration'] * 16000) == frames
                position += frames
                assert segment['done']
            assert position == hours * 3600 * 16000
            assert sum(calls) == position
            assert result['transcript'].count('Parte simulata') == len(calls)
            return {'hours':hours, 'duration_seconds':result['duration'],
                    'segments':len(calls), 'max_segment_seconds':max(calls)/16000,
                    'audio_bytes':sum(p.stat().st_size for p in folder.glob('*.wav')),
                    'elapsed_seconds':round(time.perf_counter()-started, 2),
                    'remote_api':'simulated', 'all_frames_preserved':True}
        finally:
            service.close()


if __name__ == '__main__':
    results = [check(hours) for hours in (2, 3)]
    destination = Path(__file__).resolve().parent / 'data' / 'validation' / 'long-audio-results.json'
    destination.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))
