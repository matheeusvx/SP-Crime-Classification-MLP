"""Regressão editorial: remoção explícita não deve virar dispensa de integridade."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('documentacao', ROOT/'src/maintenance56/documentation.py')
documentation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(documentation)


class RevisaoEditorial(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.addCleanup(self.directory.cleanup)
        self.before = b'notebook historico original'
        self.expected = hashlib.sha256(self.before).hexdigest()
        (self.root/'docs').mkdir()
        (self.root/'notebooks').mkdir()
        self.target = self.root/'notebooks/novo.ipynb'
        self.target.write_bytes(b'notebook consolidado validado')
        self.name = 'notebooks/antigo.ipynb'
        self.entry = {'before_commit': 'commit-fixo', 'before_sha256': self.expected,
                      'action': 'removed', 'replacement': 'notebooks/novo.ipynb',
                      'after_sha256': hashlib.sha256(self.target.read_bytes()).hexdigest()}
        self.journal = self.root/'docs/consolidacao_manifesto.json'
        self.save()

    def save(self):
        self.journal.write_text(json.dumps({'files': {self.name: self.entry}}), encoding='utf-8')

    def verify(self):
        with patch.object(documentation.subprocess, 'check_output', return_value=self.before):
            return documentation.verify_documentation_revision(self.root, self.name, self.expected)

    def test_remocao_explicita_confere_blob_e_destino(self):
        self.assertTrue(self.verify())

    def test_destino_adulterado_nao_e_aceito(self):
        self.target.write_bytes(b'alteracao nao registrada')
        with self.assertRaisesRegex(AssertionError, 'Revisão editorial divergente'):
            self.verify()

    def test_notebook_antigo_recriado_nao_e_aceito(self):
        (self.root/self.name).write_bytes(self.before)
        with self.assertRaisesRegex(AssertionError, 'Notebook histórico recriado'):
            self.verify()

    def test_hash_anterior_forjado_nao_e_aceito(self):
        self.entry['before_sha256'] = '0'*64
        self.save()
        with self.assertRaisesRegex(AssertionError, 'Blob anterior divergente'):
            self.verify()

    def test_arquivo_nao_registrado_nao_recebe_excecao(self):
        self.assertFalse(documentation.verify_documentation_revision(self.root, 'src/outro.py', '0'*64))


if __name__ == '__main__':
    unittest.main()
