"""Crea uno ZIP del programma senza chiavi, archivio personale o ambienti Python."""
import argparse
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from version import __version__

PUBLIC_FILES = (
    'main.py', 'web_app.py', 'lesson_service.py', 'local_runtime.py', 'transcript_tools.py',
    'audio_processing.py', 'audio_capture.py', 'audio_worker.py', 'ai_client.py', 'demo_client.py',
    'gui.py', 'utils.py', 'shared_state.py', 'config_template.py', 'verifica_ambiente.py',
    'verifica_locale.py', 'verifica_lezioni_lunghe.py', 'prepara_trasferimento.py',
    'installa_windows.cmd', 'avvia_lezione.cmd', 'avvia_desktop.cmd', 'avvia_prova.cmd',
    'requirements.txt', 'requirements-lock.txt', 'readme.md',
    'version.py', 'app_errors.py', 'CHANGELOG.md',
)


def create_package(root, destination):
    root = Path(root).resolve()
    destination = Path(destination).resolve()
    files = [root / name for name in PUBLIC_FILES
             if (root / name).is_file() and not (root / name).is_symlink()]
    for folder in ('web', 'tests', 'docs'):
        files.extend(p for p in (root / folder).rglob('*') if p.is_file() and
                     not p.is_symlink() and root in p.resolve().parents and
                     '__pycache__' not in p.parts and p.suffix.lower() in ('.py', '.cjs', '.js', '.css', '.html', '.md'))
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Non sovrascrivere pacchetti precedenti senza che l'utente li rinomini.
    with ZipFile(destination, 'x', ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, Path('AssistenteLezione') / path.relative_to(root))
    return len(files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(f'dist/AssistenteLezione-{__version__}.zip'))
    args = parser.parse_args()
    count = create_package(Path(__file__).resolve().parent, args.output)
    print(f'{count} file inclusi: {args.output.resolve()}')
    print('Esclusi config.py, chiavi, lezioni, modelli, ambienti Python e log.')
