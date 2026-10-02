"""Configurazione esplicita e verificabile della trascrizione sul PC."""
import os
from dataclasses import asdict, dataclass

LOCAL_MODELS = ('base', 'small', 'medium', 'large-v3-turbo', 'large-v3')


@dataclass(frozen=True)
class LocalRuntime:
    device: str = 'cpu'
    compute_type: str = 'int8'
    cpu_threads: int = max(1, min(8, (os.cpu_count() or 4) - 2))
    device_index: int = 0

    @classmethod
    def from_config(cls, config=None):
        def read(name, default):
            return os.getenv('LESSON_' + name, getattr(config, name, default))
        device = str(read('LOCAL_DEVICE', 'cpu')).lower()
        precision = str(read('LOCAL_COMPUTE_TYPE', '')).lower() or ('float16' if device == 'cuda' else 'int8')
        try:
            settings = cls(device, precision, int(read('LOCAL_CPU_THREADS', cls.cpu_threads)),
                           int(read('LOCAL_DEVICE_INDEX', 0)))
        except (TypeError, ValueError) as exc:
            raise ValueError('LOCAL_CPU_THREADS e LOCAL_DEVICE_INDEX devono essere numeri interi.') from exc
        settings.validate()
        return settings

    def validate(self):
        if self.device not in ('cpu', 'cuda'):
            raise ValueError('LOCAL_DEVICE deve essere cpu oppure cuda (NVIDIA).')
        if self.compute_type not in ('int8', 'float32', 'float16', 'int8_float16', 'int8_float32'):
            raise ValueError('LOCAL_COMPUTE_TYPE non valido.')
        if not 1 <= self.cpu_threads <= 64 or self.device_index < 0:
            raise ValueError('Usa 1–64 thread CPU e un indice GPU maggiore o uguale a zero.')

    def public(self):
        return asdict(self)

    def model_options(self, model_root):
        import ctranslate2
        self.validate()
        try:
            if self.device == 'cuda' and ctranslate2.get_cuda_device_count() <= self.device_index:
                raise ValueError('La GPU NVIDIA richiesta non è disponibile. Verifica driver e indice, oppure scegli cpu.')
            supported = ctranslate2.get_supported_compute_types(self.device, self.device_index)
        except RuntimeError as exc:
            raise ValueError('Motore locale non disponibile. Esegui verifica_locale.py e controlla driver e librerie NVIDIA.') from exc
        if self.compute_type not in supported:
            raise ValueError(f'La precisione {self.compute_type} non è supportata su {self.device}. Disponibili: {", ".join(sorted(supported))}.')
        return dict(device=self.device, device_index=self.device_index, compute_type=self.compute_type,
                    cpu_threads=self.cpu_threads, download_root=str(model_root))


def load_local_model(name, model_root, runtime, allow_download=True):
    if name not in LOCAL_MODELS:
        raise ValueError('Modello locale non previsto.')
    from faster_whisper import WhisperModel
    from huggingface_hub.errors import LocalEntryNotFoundError
    options = runtime.model_options(model_root)
    try:
        return WhisperModel(name, local_files_only=True, **options)
    except LocalEntryNotFoundError:
        if not allow_download:
            raise ValueError('Modello non presente sul disco. Ripeti con --download per scaricarlo.') from None
        return WhisperModel(name, **options)
