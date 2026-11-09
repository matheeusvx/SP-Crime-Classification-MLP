"""Executa os 8 testes originais sem sobrescrever o relatorio da Etapa 1."""
from ml.runtime import ROOT,OUT,json_write
import subprocess
import sys
import re
import os

def run():
    suites=[]
    for pattern in ['test_integridade.py','test_ml_pipeline.py']:
        env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'src');env['PYTHONIOENCODING']='utf-8'
        result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p',pattern,'-v'],cwd=ROOT,env=env,text=True,encoding='utf-8',capture_output=True)
        log=result.stdout+result.stderr;print(log,flush=True)
        (OUT/(pattern.replace('.py','.log'))).write_text(log,encoding='utf-8')
        match=re.search(r'Ran (\d+) tests?',log)
        suites.append({'arquivo':pattern,'executados':int(match.group(1)) if match else 0,
          'falhas':int(re.search(r'failures=(\d+)',log).group(1)) if 'failures=' in log else 0,
          'erros':int(re.search(r'errors=(\d+)',log).group(1)) if 'errors=' in log else (int(result.returncode!=0)),
          'sucesso':result.returncode==0 and match is not None})
    json_write(OUT/'testes_etapa2.json',suites)
    if not all(s['sucesso'] for s in suites):raise SystemExit(1)
if __name__=='__main__':run()
