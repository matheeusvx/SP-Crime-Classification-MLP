from final5.common import *
import os,subprocess,sys,re,argparse

def run(phase):
    results=[]
    cases=['test_integridade','test_ml_pipeline','test_robustez_ml','test_experimentos_ml','test_modelo_final.FinalPre'] if phase=='pre' else ['test_modelo_final.FinalPost']
    for case in cases:
        env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+str(ROOT/'tests');env['PYTHONIOENCODING']='utf-8'
        r=subprocess.run([sys.executable,'-m','unittest',case,'-v'],cwd=ROOT,env=env,text=True,encoding='utf-8',capture_output=True)
        log=r.stdout+r.stderr;(OUT/f'testes_{phase}_{case}.log').write_text(log,encoding='utf-8');print(log,flush=True)
        match=re.search(r'Ran (\d+) tests?',log)
        results.append({'suite':case,'executados':int(match.group(1)) if match else 0,'falhas':int(re.search(r'failures=(\d+)',log).group(1)) if 'failures=' in log else 0,
          'erros':int(re.search(r'errors=(\d+)',log).group(1)) if 'errors=' in log else int(r.returncode!=0),'sucesso':r.returncode==0 and match is not None})
    report={'phase':phase,'executed_at':now(),'manifest_sha256':sha256(FINAL/'manifesto.json'),'passed':all(r['sucesso'] for r in results),'suites':results}
    json_write(OUT/('testes_previos.json' if phase=='pre' else 'testes_posteriores.json'),report)
    if not report['passed']:raise SystemExit(1)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['pre','post']);run(p.parse_args().phase)
