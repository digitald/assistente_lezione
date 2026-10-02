import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import soundfile as sf

from lesson_service import LessonService
from web_app import create_app


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.service = LessonService(self.temp.name)
        self.app = create_app(self.service, demo=True)
        self.client = self.app.test_client()
        self.token = self.client.get('/api/state').json['token']
        self.headers = {'X-Local-Token': self.token}

    def tearDown(self):
        self.service.close()
        self.temp.cleanup()

    def post(self, path, data=None):
        return self.client.post(path, json=data or {}, headers=self.headers)

    def new(self):
        response = self.post('/api/lessons', {'title': 'Lezione di prova', 'docente': 'Mario Rossi', 'materia': 'Scienze'})
        self.assertEqual(response.status_code, 201)
        return response.json['id']

    def test_demo_record_pause_stop_edit_notes_download(self):
        lesson_id = self.new()
        prefix = '/api/lessons/' + lesson_id
        self.assertEqual(self.post(prefix + '/start').json['status'], 'recording')
        self.assertEqual(self.post(prefix + '/pause').json['status'], 'paused')
        self.assertEqual(self.post(prefix + '/pause').json['status'], 'recording')
        self.assertEqual(self.post(prefix + '/stop').status_code, 200)
        self.service.jobs.join()
        self.assertIn('PROVA SIMULATA', self.client.get(prefix).json['transcript'])
        self.assertEqual(self.post(prefix + '/text', {'transcript': 'Testo revisionato dal docente'}).status_code, 200)
        self.assertEqual(self.post(prefix + '/notes').status_code, 200)
        self.service.jobs.join()
        self.assertIn('Testo revisionato', self.client.get(prefix).json['notes'])
        with self.client.get(prefix + '/download/transcript') as response:
            self.assertIn(b'Testo revisionato', response.data)
        with self.client.get(prefix + '/download/notes') as response:
            self.assertIn('notes', response.headers['Content-Disposition'])

    def test_requires_token_and_local_host_and_hides_config(self):
        self.assertEqual(self.client.post('/api/lessons', json={'title':'test'}).status_code, 403)
        self.assertEqual(self.client.get('/api/state', headers={'Host':'evil.example'}).status_code, 403)
        self.assertEqual(self.client.get('/config.py').status_code, 404)
        self.assertEqual(self.client.get('/static/../../config.py').status_code, 404)
        self.assertNotIn('OPENAI_API_KEY', self.client.get('/api/state').get_data(as_text=True))

    def test_quick_start_without_profile_metadata_during_recording_and_after_stop(self):
        self.assertEqual(self.service.get_profile()['name'], '')
        response = self.post('/api/lessons/quick-start')
        self.assertEqual(response.status_code, 201)
        lesson = response.json
        self.assertEqual(lesson['status'], 'recording')
        self.assertTrue(lesson['metadata_pending'])
        self.assertEqual(self.post('/api/lessons/quick-start').status_code, 400)
        self.assertEqual(len(self.service.list_lessons()), 1)
        prefix = '/api/lessons/' + lesson['id']
        fields = dict(title='Lezione iniziata al volo', docente='Docente', course='Design', materia='Grafica', year='1', section='a',
                      status='ready', engine='local', transcript='non autorizzato')
        saved = self.post(prefix + '/metadata', fields).json
        self.assertEqual(saved['status'], 'recording')
        self.assertEqual(saved['engine'], 'demo')
        self.assertEqual(saved['transcript'], '')
        self.assertFalse(saved['metadata_pending'])
        self.assertEqual(self.service.recording['id'], lesson['id'])
        self.assertEqual(self.post(prefix + '/metadata', {'year':'999'}).status_code, 400)
        self.post(prefix + '/stop')
        self.service.jobs.join()
        saved = self.post(prefix + '/metadata', {'title': 'Titolo dopo la registrazione'}).json
        self.assertIn('PROVA SIMULATA', saved['transcript'])
        self.assertEqual(saved['course'], 'Design')
        self.assertEqual(self.service.get_profile()['name'], '')
        self.service.move(lesson['id'], 'archived')
        self.assertEqual(self.post(prefix + '/metadata', fields).status_code, 400)

    def test_quick_start_microphone_failure_keeps_recoverable_lesson(self):
        with patch.object(self.service, 'start', side_effect=ValueError('Microfono non disponibile')):
            lesson = self.service.quick_start()
        self.assertEqual(lesson['engine'], 'openai')
        self.assertEqual(lesson['model'], 'gpt-transcribe')
        self.assertEqual(lesson['status'], 'prepared')
        self.assertTrue(lesson['error'])
        self.assertIsNone(self.service.recording)
        self.assertEqual(len(self.service.list_lessons()), 1)
        self.assertEqual(self.service.get(lesson['id'])['id'], lesson['id'])

    def test_profile_rejected_token_has_recoverable_code_without_saving(self):
        fields = {'name': 'Docente', 'assignments': [
            {'course': 'Design', 'teaching': 'Grafica', 'year': '1', 'section': 'a'}]}
        rejected = self.client.post('/api/profile', json=fields, headers={'X-Local-Token': 'old-session'})
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(rejected.json['code'], 'local_token_expired')
        self.assertEqual(self.service.get_profile()['name'], '')
        fresh = self.client.get('/api/state').json['token']
        saved = self.client.post('/api/profile', json=fields, headers={'X-Local-Token': fresh})
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.service.get_profile()['name'], 'Docente')

    def test_template_updates_without_restarting_the_server(self):
        from jinja2 import DictLoader
        templates = {'index.html': '<html>Versione precedente</html>'}
        self.app.jinja_loader = DictLoader(templates)
        self.assertIn('Versione precedente', self.client.get('/').get_data(as_text=True))
        templates['index.html'] = '<html>Nuovi comandi del pannello</html>'
        self.assertIn('Nuovi comandi del pannello', self.client.get('/').get_data(as_text=True))

    def test_larger_local_models_can_be_selected_without_loading_them(self):
        for model in ('medium', 'large-v3', 'large-v3-turbo'):
            lesson = self.service.create({'title': 'Modello locale', 'engine': 'local', 'model': model})
            self.assertEqual(lesson['model'], model)
        self.assertEqual(self.service.local_models, {})
        self.assertEqual(self.service.status()['local_runtime']['device'], 'cpu')

    def test_state_reads_compact_summaries_and_tracks_revisions(self):
        lesson_id = self.new()
        before = self.service.get(lesson_id)['revision']
        self.service.save_text(lesson_id, transcript='Testo lungo ' * 100000)
        with patch.object(self.service, 'list_lessons', side_effect=AssertionError('Full archive read')):
            response = self.client.get('/api/state')
        summary = response.json['lessons'][0]
        self.assertLess(len(response.data), 3000)
        self.assertNotIn('transcript', summary)
        self.assertNotIn('segments', summary)
        self.assertNotEqual(summary['revision'], before)
        self.assertEqual(summary['revision'], self.service.get(lesson_id)['revision'])

    def test_old_database_migrates_without_changing_text(self):
        self.service.close()
        lesson = {'id': 'a' * 32, 'created_at': '2026-01-01', 'status': 'ready',
                  'transcript': 'Testo originale', 'notes': 'Appunti originali', 'segments': []}
        with sqlite3.connect(self.service.root / 'archive.sqlite3') as db:
            db.execute('DROP TABLE lessons')
            db.execute('CREATE TABLE lessons (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            db.execute('INSERT INTO lessons VALUES (?, ?)', (lesson['id'], json.dumps(lesson)))
        db.close()
        self.service = LessonService(self.temp.name)
        self.assertEqual(self.service.get(lesson['id']), lesson)
        self.assertNotIn('transcript', self.service.list_summaries()[0])
        updated = self.service.update(lesson['id'], progress='Salvata')
        self.assertTrue(updated['revision'])
        self.assertEqual(updated['transcript'], 'Testo originale')

    def test_capture_warning_survives_transcription(self):
        lesson_id = self.new()
        self.service.start(lesson_id)
        self.service.recording['error'] = 'Interruzione del microfono'
        self.service.stop(lesson_id)
        self.service.jobs.join()
        lesson = self.service.get(lesson_id)
        self.assertEqual(lesson['capture_warning'], 'Interruzione del microfono')
        self.assertEqual(lesson['status'], 'ready')

    def test_markdown_download_preserves_structure_and_rejects_missing_notes(self):
        lesson_id = self.new()
        path = f'/api/lessons/{lesson_id}/download/notes-markdown'
        self.assertEqual(self.client.get(path).status_code, 400)
        notes = '# Lezione\n\n## Argomento\n\n- **Definizione**: contenuto.\n'
        self.service.save_text(lesson_id, notes=notes)
        with self.client.get(path) as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data.decode('utf-8'), notes)
            self.assertIn('.md', response.headers['Content-Disposition'])
            self.assertEqual(response.mimetype, 'text/markdown')

    def test_failed_notes_generation_keeps_previous_document(self):
        lesson = self.service.create({'title': 'Lezione', 'engine': 'openai'})
        self.service.api_key = 'test'
        self.service.save_text(lesson['id'], transcript='Fonte', notes='# Appunti revisionati\n')
        with patch('lesson_service.LessonService.cloud_client'), patch('ai_client.AIClient') as client:
            client.return_value.summarize_transcript.side_effect = ValueError('Risposta incompleta')
            self.service.enqueue(lesson['id'], 'notes')
            self.service.jobs.join()
        updated = self.service.get(lesson['id'])
        self.assertEqual(updated['notes'], '# Appunti revisionati\n')
        self.assertEqual(updated['status'], 'failed')
        self.assertEqual((self.service.root / lesson['id'] / 'notes.txt').read_text(encoding='utf-8'), updated['notes'])

    def test_archive_trash_restore_preserve_contents_and_survive_restart(self):
        lesson_id = self.new()
        prefix = '/api/lessons/' + lesson_id
        self.service.save_text(lesson_id, transcript='Lezione da conservare', notes='Appunti salvati')
        audio = self.service.root / lesson_id / 'recording.wav'
        sf.write(audio, np.zeros(16000), 16000)
        self.service.update(lesson_id, audio=audio.name)
        for collection in ('archived', 'trash'):
            response = self.post(prefix + '/move', {'collection': collection})
            self.assertEqual(response.json['collection'], collection)
            self.assertEqual(self.post(prefix + '/text', {'transcript': 'errore'}).status_code, 400)
            self.assertEqual(self.post(prefix + '/retry').status_code, 400)
            with self.client.get(prefix + '/download/transcript') as download:
                self.assertIn(b'Lezione da conservare', download.data)
        self.service.close()
        self.service = LessonService(self.temp.name)
        self.assertEqual(self.service.get(lesson_id)['collection'], 'trash')
        restored = self.service.move(lesson_id, 'active')
        self.assertEqual(restored['transcript'], 'Lezione da conservare')
        self.assertEqual(restored['notes'], 'Appunti salvati')
        self.assertTrue(audio.exists())

    def test_cannot_move_busy_lessons_and_old_lessons_remain_editable(self):
        lesson_id = self.new()
        prefix = '/api/lessons/' + lesson_id
        for status in ('recording', 'paused', 'queued', 'transcribing', 'notes'):
            self.service.update(lesson_id, status=status)
            self.assertEqual(self.post(prefix + '/move', {'collection':'trash'}).status_code, 400)
        self.service.update(lesson_id, status='prepared')
        old = self.service.get(lesson_id)
        old.pop('collection')
        self.service.put(old)
        self.assertEqual(self.post(prefix + '/text', {'transcript':'Archivio precedente'}).status_code, 200)
        self.assertEqual(self.post(prefix + '/move', {'collection':'invalid'}).status_code, 400)
        self.assertEqual(self.client.post(prefix + '/move', json={'collection':'trash'}).status_code, 403)

    def test_permanent_delete_requires_trash_removes_files_and_prevents_reimport(self):
        legacy = self.service.root / 'legacy'
        legacy.mkdir()
        source = legacy / 'trascrizione_Prova.txt'
        source.write_text('Lezione precedente', encoding='utf-8')
        self.service.import_legacy(legacy, legacy)
        lesson_id = self.service.list_lessons()[0]['id']
        prefix = '/api/lessons/' + lesson_id
        self.assertEqual(self.client.delete(prefix, headers=self.headers).status_code, 400)
        self.service.move(lesson_id, 'trash')
        self.assertEqual(self.client.delete(prefix).status_code, 403)
        self.assertEqual(self.client.delete(prefix, headers=self.headers).status_code, 200)
        self.assertFalse((self.service.root / lesson_id).exists())
        self.assertEqual(self.client.get(prefix).status_code, 404)
        self.service.import_legacy(legacy, legacy)
        self.assertEqual(self.service.list_lessons(), [])
        self.assertEqual(source.read_text(encoding='utf-8'), 'Lezione precedente')

    def test_teacher_profile_persists_and_lessons_keep_class_snapshot(self):
        self.assertEqual(self.client.get('/api/profile').json['assignments'], [])
        fields = {'name':'Docente di prova', 'assignments':[
            {'course':'Communication Design', 'teaching':'Grafica Multimediale I', 'year':'1', 'section':'a'},
            {'course':'Communication Design', 'teaching':'Grafica Multimediale I', 'year':'1', 'section':'b'}]}
        self.assertEqual(self.client.post('/api/profile', json=fields).status_code, 403)
        profile = self.post('/api/profile', fields).json
        lesson = self.post('/api/lessons', {'title':'04 - Interfaccia di Photoshop',
            'assignment_id':profile['assignments'][0]['id'], 'docente':'Nome errato', 'materia':'Materia errata'}).json
        self.assertEqual(lesson['docente'], 'Docente di prova')
        self.assertEqual(lesson['course'], 'Communication Design')
        self.assertEqual(lesson['materia'], 'Grafica Multimediale I')
        self.assertEqual(lesson['year'] + lesson['section'], '1a')
        profile['name'] = 'Nome modificato'
        profile['assignments'] = profile['assignments'][1:]
        self.post('/api/profile', profile)
        self.service.close()
        self.service = LessonService(self.temp.name)
        self.assertEqual(self.service.get_profile()['name'], 'Nome modificato')
        self.assertEqual(self.service.get(lesson['id'])['docente'], 'Docente di prova')

    def test_profile_rejects_incomplete_duplicate_and_unknown_classes(self):
        assignment = {'course':'Communication Design', 'teaching':'Grafica Multimediale I', 'year':'1', 'section':'a'}
        for fields in ({'name':'', 'assignments':[assignment]},
                       {'name':'Docente', 'assignments':[]},
                       {'name':'Docente', 'assignments':[assignment, assignment]},
                       {'name':'Docente', 'assignments':[dict(assignment, year='0')]},
                       {'name':'Docente', 'assignments':[dict(assignment, teaching='')]}):
            self.assertEqual(self.post('/api/profile', fields).status_code, 400)
        self.assertEqual(self.post('/api/lessons', {'title':'Test', 'assignment_id':'missing'}).status_code, 400)

    def test_archive_survives_restart_and_legacy_import_is_repeatable(self):
        lesson_id = self.new()
        self.service.save_text(lesson_id, transcript='Testo persistente')
        legacy = Path(self.temp.name) / 'legacy'
        legacy.mkdir()
        (legacy / 'trascrizione_Mario_Rossi_Scienze_20261002_1200.txt').write_text('Archivio precedente', encoding='utf-8')
        self.service.import_legacy(legacy, legacy)
        self.service.import_legacy(legacy, legacy)
        self.assertEqual(len(self.service.list_lessons()), 2)
        self.service.close()
        self.service = LessonService(self.temp.name)
        self.assertEqual(self.service.get(lesson_id)['transcript'], 'Testo persistente')

    def test_recovery_marks_interrupted_and_keeps_audio(self):
        lesson_id = self.new()
        path = Path(self.temp.name) / lesson_id / 'recording.wav'
        sf.write(path, np.zeros(16000), 16000)
        self.service.update(lesson_id, status='recording', audio='recording.wav')
        self.service.close()
        self.service = LessonService(self.temp.name)
        self.assertEqual(self.service.get(lesson_id)['status'], 'interrupted')
        self.assertTrue(path.exists())

    def test_real_capture_and_cloud_retry_keep_finished_segments(self):
        client = MagicMock()
        results = iter([SimpleNamespace(text='prima parte'), RuntimeError('failure'), SimpleNamespace(text='ultima parte')])
        def transcribe(**params):
            self.assertEqual(params['model'], 'gpt-transcribe')
            self.assertEqual(params['extra_body'], {'languages':['it']})
            result = next(results)
            if isinstance(result, Exception):
                raise result
            return result
        client.audio.transcriptions.create.side_effect = transcribe
        self.service.api_key = 'test'
        self.service.client_factory = lambda: client
        lesson = self.service.create({'title':'Reale', 'engine':'openai'})
        folder = Path(self.temp.name) / lesson['id']
        with patch('lesson_service.sd.InputStream', return_value=MagicMock()), patch('lesson_service.sd.check_input_settings'):
            self.service.start(lesson['id'])
            callback = __import__('lesson_service').sd.InputStream.call_args.kwargs['callback']
            data = np.ones((16000,1), dtype=np.float32)*0.01
            callback(data,len(data),None,None)
            self.service.pause(lesson['id'])
            callback(data,len(data),None,None)
            self.assertEqual(self.service.recording['frames'],16000)
            self.service.pause(lesson['id'])
            for name in ['segment_00000.wav','segment_00001.wav']:
                sf.write(folder/name,data,16000)
            self.service.update(lesson['id'],segments=[{'file':f'segment_{i:05d}.wav','start':i,'duration':1,'done':False,'text':''} for i in range(2)])
            self.service.stop(lesson['id'])
        self.service.jobs.join()
        self.assertEqual(self.service.get(lesson['id'])['status'],'failed')
        self.assertIn('prima parte',self.service.get(lesson['id'])['transcript'])
        self.service.enqueue(lesson['id'],'transcribe')
        self.service.jobs.join()
        updated = self.service.get(lesson['id'])
        self.assertEqual(updated['status'],'ready')
        self.assertEqual(updated['transcript'].count('prima parte'),1)
        self.assertIn('ultima parte',updated['transcript'])
        self.assertEqual(client.audio.transcriptions.create.call_count,3)
        self.assertEqual(sf.info(folder/'recording.wav').frames,16000)

    def test_import_normalizes_audio_and_saves_final_segment(self):
        class Model:
            def transcribe(self,waveform,**kwargs):
                self.samples = len(waveform)
                return [SimpleNamespace(text=' testo italiano ')],None
        model=Model()
        self.service.local_models['base']=model
        app=create_app(self.service)
        client=app.test_client()
        headers={'X-Local-Token':client.get('/api/state').json['token']}
        lesson=client.post('/api/lessons',json={'title':'Audio importato'},headers=headers).json
        audio=io.BytesIO()
        sf.write(audio,np.ones((24000,2),dtype=np.float32)*0.01,48000,format='WAV')
        audio.seek(0)
        result=client.post(f"/api/lessons/{lesson['id']}/import",data={'audio':(audio,'lezione.wav')},headers=headers)
        self.assertEqual(result.status_code,200)
        self.service.jobs.join()
        updated=self.service.get(lesson['id'])
        self.assertEqual(updated['status'],'ready',updated['error'])
        self.assertIn('testo italiano',updated['transcript'])
        self.assertEqual(model.samples,8000)
        self.assertAlmostEqual(updated['duration'],0.5,places=2)

    def test_import_m4a_recording_decodes_before_transcription(self):
        import av
        class Model:
            def transcribe(self, waveform, **kwargs):
                self.samples = len(waveform)
                return [SimpleNamespace(text='Registrazione importata')], None
        model = Model()
        self.service.local_models['base'] = model
        encoded = io.BytesIO()
        with av.open(encoded, mode='w', format='mp4') as container:
            stream = container.add_stream('aac', rate=48000)
            stream.layout = 'mono'
            samples = np.sin(np.arange(48000) * 2 * np.pi * 440 / 48000).astype('float32') * 0.05
            frame = av.AudioFrame.from_ndarray(samples.reshape(1, -1), format='fltp', layout='mono')
            frame.sample_rate = 48000
            for packet in stream.encode(frame):
                container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        encoded.seek(0)
        app = create_app(self.service)
        client = app.test_client()
        headers = {'X-Local-Token': client.get('/api/state').json['token']}
        lesson = client.post('/api/lessons', json={'title': 'Registrazione esterna'}, headers=headers).json
        response = client.post(f"/api/lessons/{lesson['id']}/import",
                               data={'audio': (encoded, 'Registrazione.M4A')}, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.service.jobs.join()
        updated = self.service.get(lesson['id'])
        self.assertEqual(updated['status'], 'ready', updated['error'])
        self.assertEqual(updated['audio'], 'imported.m4a')
        self.assertIn('Registrazione importata', updated['transcript'])
        self.assertGreaterEqual(model.samples, 16000)


if __name__=='__main__':
    unittest.main()
