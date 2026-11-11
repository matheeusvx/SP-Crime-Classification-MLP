"""Confere originais históricos e revisões explicitamente autorizadas.

Os manifestos antigos continuam intocados. Revisões não são tratadas como
bytes históricos: ambos os estados precisam ter seus hashes comprovados.
"""
from ml.runtime import ROOT, sha256
import hashlib
import json
import subprocess

OUT = ROOT/'reports/pos_auditoria'
SNAPSHOT = 'snapshot-pos-auditoria-antes-correcoes'


def verify_history(manifest):
    from maintenance56.documentation import verify_documentation_revision
    revisions = json.loads((OUT/'revisoes_autorizadas.json').read_text(encoding='utf-8'))['files']
    for name, expected in manifest.items():
        if verify_documentation_revision(ROOT, name, expected, revisions.get(name)):
            continue
        actual = sha256(ROOT/name)
        if actual == expected:
            continue
        revision = revisions.get(name)
        if not revision or revision['before_sha256'] != expected or revision['after_sha256'] != actual:
            raise AssertionError('Alteração histórica não autorizada: '+name)
        original = subprocess.check_output(['git', 'show', SNAPSHOT+':'+name], cwd=ROOT)
        if hashlib.sha256(original).hexdigest() != expected:
            raise AssertionError('Snapshot histórico não corresponde ao manifesto: '+name)
    return len(manifest)


def verify_snapshot():
    state = json.loads((OUT/'estado_anterior.json').read_text(encoding='utf-8'))
    return verify_history(state['files'])
