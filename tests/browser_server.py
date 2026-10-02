"""Server isolato per check_browser.cjs. Avvio: python tests/browser_server.py."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lesson_service import LessonService
from web_app import create_app
from waitress import serve


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='lesson-ui-review-') as folder:
        service = LessonService(folder)
        service.save_profile({'name': 'Docente demo', 'assignments': [
            {'course': 'Communication Design', 'teaching': 'Grafica Multimediale I', 'year': '1', 'section': 'a'}]})
        lesson = service.create({'title': '01 - Introduzione al progetto', 'engine': 'demo'})
        service.save_text(lesson['id'], transcript='Una lezione di prova per verificare revisione, salvataggio e appunti.')
        service.update(lesson['id'], status='ready')
        print('Archivio temporaneo di collaudo: http://127.0.0.1:8877', flush=True)
        try:
            serve(create_app(service, demo=True), host='127.0.0.1', port=8877)
        finally:
            service.close()
