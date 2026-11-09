"""Orquestracao reproduzivel: ingestao -> auditoria -> preparacao -> relatorios."""
import argparse
from ingest import ingest, ROOT
from audit import audit
from prepare import prepare
from pathlib import Path
from source_metadata import extract_support
import subprocess
import sys

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input-dir',type=Path,default=Path('D:/'))
    p.add_argument('--skip-ingest',action='store_true'); p.add_argument('--force',action='store_true'); a=p.parse_args()
    if not a.skip_ingest:
        for year in (2023,2024,2025): ingest(a.input_dir/f'CelularesSubtraidos_{year}.xlsx',year,a.force)
    (ROOT/'reports/tables').mkdir(parents=True,exist_ok=True)
    extract_support(a.input_dir)
    audit()
    prepare()
    subprocess.run([sys.executable,str(ROOT/'tests/test_integridade.py')],check=True,cwd=ROOT)
    from report import report
    report()
