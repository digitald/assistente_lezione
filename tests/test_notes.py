import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ai_client import AIClient


class NotesTests(unittest.TestCase):
    def setUp(self):
        with patch('ai_client.openai.OpenAI'):
            self.client = AIClient('test')
        self.client.client = MagicMock()

    def response(self, content, finish='stop'):
        self.client.client.chat.completions.create.return_value = SimpleNamespace(choices=[
            SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish)])

    def test_empty_source_does_not_call_service(self):
        self.assertEqual(self.client.summarize_transcript('  '), '')
        self.client.client.chat.completions.create.assert_not_called()

    def test_source_and_metadata_are_data_and_markdown_wrapper_is_removed(self):
        self.response('```markdown\n# Lezione\n\n## Concetti\n\n**Forma** e contenuto.\n```')
        result = self.client.summarize_transcript('Testo originale', {'title': 'Lezione'})
        self.assertEqual(result, '# Lezione\n\n## Concetti\n\n**Forma** e contenuto.\n')
        import json
        messages = self.client.client.chat.completions.create.call_args.kwargs['messages']
        self.assertEqual(json.loads(messages[1]['content'])['trascrizione'], 'Testo originale')
        self.assertEqual(json.loads(messages[1]['content'])['metadati_lezione']['title'], 'Lezione')

    def test_truncated_refused_or_empty_result_is_not_accepted(self):
        for content, finish in [('# Testo incompleto', 'length'), ('', 'content_filter'), (None, 'stop'), ('   ', 'stop')]:
            with self.subTest(content=content, finish=finish):
                self.response(content, finish)
                with self.assertRaises(ValueError):
                    self.client.summarize_transcript('Trascrizione')
