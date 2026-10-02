import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

from local_runtime import LocalRuntime
from prepara_trasferimento import create_package
from transcript_tools import readable_text, compose_transcript


class LocalConfigurationTests(unittest.TestCase):
    def test_configuration_cpu_cuda_and_environment_override(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(LocalRuntime.from_config().device, 'cpu')
            self.assertEqual(LocalRuntime.from_config(SimpleNamespace(LOCAL_DEVICE='cuda')).compute_type, 'float16')
        with patch.dict(os.environ, {'LESSON_LOCAL_DEVICE': 'cuda', 'LESSON_LOCAL_COMPUTE_TYPE': 'int8_float16'}):
            self.assertEqual(LocalRuntime.from_config().compute_type, 'int8_float16')

    def test_invalid_options_and_unavailable_gpu_fail_explicitly(self):
        with patch.dict(os.environ, {'LESSON_LOCAL_CPU_THREADS': '0'}):
            with self.assertRaises(ValueError):
                LocalRuntime.from_config()
        with patch('ctranslate2.get_cuda_device_count', return_value=0):
            with self.assertRaisesRegex(ValueError, 'GPU NVIDIA'):
                LocalRuntime('cuda', 'float16').model_options('models')
        with patch('ctranslate2.get_supported_compute_types', return_value={'int8'}):
            with self.assertRaisesRegex(ValueError, 'non è supportata'):
                LocalRuntime('cpu', 'float16').model_options('models')

    def test_selected_hardware_reaches_model_options(self):
        with patch('ctranslate2.get_cuda_device_count', return_value=2), patch('ctranslate2.get_supported_compute_types', return_value={'int8_float16'}):
            options = LocalRuntime('cuda', 'int8_float16', 12, 1).model_options('models')
        self.assertEqual(options['device'], 'cuda')
        self.assertEqual(options['device_index'], 1)
        self.assertEqual(options['cpu_threads'], 12)

    def test_transcript_layout_preserves_words_and_marks_hours(self):
        original = 'Prima frase.  Seconda frase importante!\nTerza frase, senza correzioni.'
        formatted = readable_text(original, paragraph_chars=25)
        self.assertEqual(original.split(), formatted.split())
        self.assertIn('\n\n', formatted)
        output = compose_transcript([
            {'start': 3661, 'done': True, 'text': original},
            {'start': 3700, 'done': False, 'text': 'non completato'},
            {'start': 3800, 'done': True, 'text': ' '}])
        self.assertTrue(output.startswith('[01:01:01] Prima frase.'))
        self.assertNotIn('non completato', output)

    def test_package_excludes_private_files_data_and_environments(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('main.py', 'config_template.py', 'config.py', 'secret.py'):
                (root / name).write_text('test')
            for dirname in ('data', '.venv', '.git', 'web'):
                (root / dirname).mkdir()
                (root / dirname / 'index.html').write_text('test')
            target = root / 'package.zip'
            create_package(root, target)
            with ZipFile(target) as archive:
                self.assertEqual(set(archive.namelist()), {
                    'AssistenteLezione/main.py', 'AssistenteLezione/config_template.py',
                    'AssistenteLezione/web/index.html'})
            with self.assertRaises(FileExistsError):
                create_package(root, target)
