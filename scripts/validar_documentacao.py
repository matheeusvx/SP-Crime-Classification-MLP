"""Valida a entrega editorial sem treinamento, datasets ou avaliação de 2025.

Use --executar para executar em memória num clone público temporário sem binários.
Dependências: nbformat; execução opcional: nbclient e ipykernel.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit

import nbformat

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT/'notebooks/GS_Classificacao_MLP_Completo.ipynb'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def links(text, base):
    # Não interpreta exemplos de comandos/código como links de navegação.
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    count = 0
    for url in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', text):
        url = url.strip('<>')
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc:
            continue
        target = (base.parent/unquote(parsed.path)).resolve() if parsed.path else base
        assert target.exists(), f'Link ausente em {base.name}: {url}'
        if parsed.fragment:
            contents = text if not parsed.path else target.read_text(encoding='utf-8')
            assert re.search(r'id=["\']'+re.escape(parsed.fragment)+r'["\']', contents), url
        count += 1
    return count


def validate():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    nbformat.validate(nb)
    assert list((ROOT/'notebooks').glob('*.ipynb')) == [NOTEBOOK]
    for cell in nb.cells:
        if cell.cell_type == 'code':
            ast.parse(cell.source)
            assert cell.execution_count is not None, 'Célula sem validação executada'
            assert all(o.output_type != 'error' for o in cell.outputs)
    optional = [c for c in nb.cells if 'reproducao-opcional-desativada' in c.metadata.get('tags', [])]
    assert len(optional) == 1
    tree = ast.parse(optional[0].source)
    flags = {n.targets[0].id: n.value.value for n in tree.body
             if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
             and isinstance(n.value, ast.Constant)}
    assert flags['REPRODUZIR_BASELINE'] is False and flags['REPRODUZIR_ETAPA4'] is False
    markdown = '\n'.join(c.source for c in nb.cells if c.cell_type == 'markdown')
    assert len(re.findall(r'^## \d{2} —', markdown, re.M)) == 10
    count = links(markdown, NOTEBOOK)
    docs = ['README.md', 'docs/consolidacao_academica.md', 'docs/etapa2_reproducao.md', 'web/README.md']
    for name in docs:
        count += links((ROOT/name).read_text(encoding='utf-8'), ROOT/name)
    # As mesmas figuras históricas são usadas sem regenerar seus pixels.
    images = re.findall(r'!\[[^\]]*\]\(([^)]+\.png)\)', markdown)
    for name in images:
        assert (NOTEBOOK.parent/name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n'), name

    manifest = json_read(ROOT/'models/final/manifesto.json')
    expected_manifest = 'b992412335c69623bdf63c9341cefaa82e0a81ae73d7d32e110f2498faa8c532'
    assert sha(ROOT/'models/final/manifesto.json') == expected_manifest
    assert (ROOT/'models/final/manifesto.sha256').read_text().strip() == expected_manifest
    hashes = manifest['inference_source_hashes'] | {
        'models/final/'+p: h for p, h in manifest['frozen_files'].items()}
    binary_absent = []
    for name, expected in hashes.items():
        path = ROOT/name
        if path.exists():
            assert sha(path) == expected, name
        else:
            assert path.suffix in {'.keras', '.joblib'}, name
            binary_absent.append(name)

    readme = (ROOT/'README.md').read_text(encoding='utf-8')
    final = json_read(ROOT/'reports/etapa5/metricas_2025.json')
    for key in ['accuracy', 'macro_f1', 'recall_roubo', 'precision_roubo', 'balanced_accuracy']:
        expected = f'{final[key]*100:.2f}%'.replace('.', ',')
        assert expected in readme, (key, expected)
    for name in ['B32', 'B64', 'B64_32']:
        run = json_read(ROOT/f'reports/etapa4/runs/{name}_full_s42.json')
        for key in ['accuracy', 'macro_f1', 'recall_roubo']:
            expected = f'{run["validation_metrics"][key]*100:.2f}%'.replace('.', ',')
            assert expected in readme, (name, key, expected)
        assert f'{run["parameters"]:,}'.replace(',', '.') in readme
    lock = json_read(ROOT/'web/frontend/package-lock.json')['packages']
    assert lock['node_modules/react']['version'] == '19.3.1'
    assert lock['node_modules/typescript']['version'] == '7.0.2'
    assert lock['node_modules/vite']['version'] == '8.3.7'
    for req in ['tensorflow==2.20.0', 'keras==3.11.3']:
        assert req in (ROOT/'requirements-final.txt').read_text()
    assert 'fastapi==0.121.*' in (ROOT/'requirements-web.txt').read_text()
    assert 'flutter' not in readme.lower() and 'dart' not in readme.lower()

    journal = json_read(ROOT/'docs/consolidacao_manifesto.json')
    sys.path.insert(0, str(ROOT/'src'))
    from maintenance56.documentation import verify_documentation_revision
    prior = json_read(ROOT/'reports/pos_auditoria/revisoes_autorizadas.json')['files']
    for name, entry in journal['files'].items():
        assert verify_documentation_revision(ROOT, name, entry['before_sha256'])
        if name in prior:
            assert verify_documentation_revision(ROOT, name, prior[name]['before_sha256'], prior[name])
    for name, expected in journal['protected_files'].items():
        assert sha(ROOT/name) == expected, 'Evidência histórica alterada: '+name
    for module in ['data', 'ml', 'diagnostics', 'experiments4', 'final5']:
        text = (ROOT/f'src/{module}/report.py').read_text(encoding='utf-8')
        tree = ast.parse(text)
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'notebook')
        function_text = ast.get_source_segment(text, function)
        assert 'GS_Classificacao_MLP_Completo.ipynb' in function_text
        assert 'write_text' not in function_text
    print(f'OK: JSON; {len(nb.cells)} células; 10 seções; {len(images)} figuras; {count} links locais/âncoras.')
    print(f'OK: métricas transcritas, versões, {len(journal["files"])} revisões e '
          f'{len(journal["protected_files"])} evidências históricas preservadas.')
    print('OK: hashes congelados.', 'Binários ausentes (esperado no clone): '+str(binary_absent) if binary_absent else '')
    return nb


def execute_readonly(nb):
    from nbclient import NotebookClient
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    # Simula o clone público: nenhum XLSX/Parquet, joblib, keras ou runtime local.
    with tempfile.TemporaryDirectory(prefix='gs-documentacao-') as temp:
        temp = Path(temp)
        clone = temp/'publico'
        public_names = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
        for name in [*public_names, 'notebooks/GS_Classificacao_MLP_Completo.ipynb']:
            source = ROOT/name
            if not source.is_file() or not name.startswith(('reports/', 'src/', 'models/final/')):
                continue
            if source.suffix in {'.keras', '.joblib', '.npz', '.parquet', '.xlsx'}:
                continue
            dest = clone/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        (clone/'notebooks').mkdir(parents=True)
        kernel_root = temp/'kernels'
        spec_dir = kernel_root/'gs-docs'
        spec_dir.mkdir(parents=True)
        (spec_dir/'kernel.json').write_text(json.dumps({
            'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
            'display_name': 'GS documentação', 'language': 'python'}), encoding='utf-8')
        manager = KernelManager(kernel_name='gs-docs',
                                kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_root)]))
        environment = dict(os.environ, IPYTHONDIR=str(temp/'ipython'),
                           JUPYTER_CONFIG_DIR=str(temp/'config'), JUPYTER_RUNTIME_DIR=str(temp/'runtime'))
        nb = nbformat.from_dict(json.loads(json.dumps(nb)))
        nb.cells.append(nbformat.v4.new_code_cell(
            "import sys\nassert 'tensorflow' not in sys.modules\n"
            "assert not list(ROOT.glob('models/**/*.keras'))\n"
            "assert not list(ROOT.glob('data/**/*.parquet'))\n"
            "print('Clone público: leitura completa sem TensorFlow, pesos ou datasets.')"))
        try:
            NotebookClient(nb, km=manager, timeout=90, record_timing=False,
                           resources={'metadata': {'path': str(clone/'notebooks')}},
                           allow_errors=False).execute(env=environment)
        finally:
            # O manager externo pertence a este script, não ao NotebookClient.
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
            manager.cleanup_resources()
        assert all(o.output_type != 'error' for c in nb.cells if c.cell_type == 'code' for o in c.outputs)
        print('OK: execução integral em clone público temporário, sem pesos/dados/TensorFlow.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--executar', action='store_true')
    args = parser.parse_args()
    notebook = validate()
    if args.executar:
        execute_readonly(notebook)
