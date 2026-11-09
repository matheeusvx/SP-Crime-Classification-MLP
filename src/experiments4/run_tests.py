from experiments4.common import *
import os,subprocess,sys,re
if __name__=='__main__':
    results=[]
    for pattern in ['test_integridade.py','test_ml_pipeline.py','test_robustez_ml.py','test_experimentos_ml.py']:
        env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'src');env['PYTHONIOENCODING']='utf-8'
        r=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p',pattern,'-v'],cwd=ROOT,env=env,text=True,encoding='utf-8',capture_output=True)
        log=r.stdout+r.stderr;(OUT/(pattern+'.log')).write_text(log,encoding='utf-8');print(log,flush=True)
        match=re.search(r'Ran (\d+) tests?',log)
        results.append({'arquivo':pattern,'executados':int(match.group(1)) if match else 0,
          'falhas':int(re.search(r'failures=(\d+)',log).group(1)) if 'failures=' in log else 0,
          'erros':int(re.search(r'errors=(\d+)',log).group(1)) if 'errors=' in log else int(r.returncode!=0),
          'sucesso':r.returncode==0 and match is not None})
    json_write(OUT/'testes.json',results)
    if not all(r['sucesso'] for r in results):raise SystemExit(1)
