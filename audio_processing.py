"""Normalizzazione condivisa da applicazione e collaudo locale."""
import soundfile as sf


def normalize_audio(source, target):
    import av
    with av.open(str(source)) as container, sf.SoundFile(target, mode='w', samplerate=16000,
                                                       channels=1, subtype='PCM_16') as output:
        resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
        for frame in container.decode(audio=0):
            for result in resampler.resample(frame):
                output.write(result.to_ndarray().reshape(-1))
        for result in resampler.resample(None):
            output.write(result.to_ndarray().reshape(-1))
