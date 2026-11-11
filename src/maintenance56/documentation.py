"""Verificação explícita de revisões editoriais, sem alterar manifestos de ML."""
import hashlib
import json
from pathlib import Path
import subprocess


def verify_documentation_revision(root: Path, name: str, expected: str, prior_revision=None) -> bool:
    journal = root/'docs/consolidacao_manifesto.json'
    if not journal.is_file():
        return False
    entry = json.loads(journal.read_text(encoding='utf-8'))['files'].get(name)
    if entry is None:
        return False
    before = entry['before_sha256']
    blob = subprocess.check_output(['git', 'show', entry['before_commit']+':'+name], cwd=root)
    if hashlib.sha256(blob).hexdigest() != before:
        raise AssertionError('Blob anterior divergente: '+name)
    if expected != before:
        if not prior_revision or prior_revision['before_sha256'] != expected or prior_revision['after_sha256'] != before:
            raise AssertionError('Cadeia histórica divergente: '+name)
        original = subprocess.check_output(['git', 'show', 'snapshot-pos-auditoria-antes-correcoes:'+name], cwd=root)
        if hashlib.sha256(original).hexdigest() != expected:
            raise AssertionError('Snapshot original divergente: '+name)
    current = root/name
    if entry['action'] == 'removed':
        if current.exists():
            raise AssertionError('Notebook histórico recriado: '+name)
        current = root/entry['replacement']
    elif entry['action'] != 'updated':
        raise AssertionError('Ação editorial desconhecida: '+name)
    if not current.is_file() or hashlib.sha256(current.read_bytes()).hexdigest() != entry['after_sha256']:
        raise AssertionError('Revisão editorial divergente: '+name)
    return True
