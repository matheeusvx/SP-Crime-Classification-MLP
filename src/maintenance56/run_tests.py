"""Regressão pós-auditoria: logs separados; sem reavaliar ou ajustar 2025."""
from ml.runtime import ROOT
from maintenance56.integrity import OUT
import os
import subprocess
import sys
import re
import json
from datetime import datetime, timezone


def run():
    cases = ['test_integridade', 'test_ml_pipeline', 'test_robustez_ml',
             'test_experimentos_ml', 'test_modelo_final.FinalPre', 'test_contrato_inferencia_seguro']
    results=[]
    for case in cases:
        env=os.environ.copy()
        env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+str(ROOT/'tests')
        env['PYTHONIOENCODING']='utf-8'
        proc=subprocess.run([sys.executable,'-m','unittest',case,'-v'],cwd=ROOT,
                            env=env,capture_output=True,text=True,encoding='utf-8')
        log=proc.stdout+proc.stderr
        (OUT/f'{case}.log').write_text(log,encoding='utf-8')
        count=re.search(r'Ran (\d+) tests?',log)
        summary={'suite':case,'executed':int(count.group(1)) if count else 0,
                 'failures':sum(int(n) for n in re.findall(r'failures=(\d+)',log)),
                 'errors':sum(int(n) for n in re.findall(r'errors=(\d+)',log)),
                 'passed':proc.returncode==0 and count is not None}
        results.append(summary);print(json.dumps(summary),flush=True)
        if not summary['passed']: print(log[-6000:],flush=True)
    report={'executed_at':datetime.now(timezone.utc).isoformat(),'suites':results,
            'executed':sum(r['executed'] for r in results),'failures':sum(r['failures'] for r in results),
            'errors':sum(r['errors'] for r in results),'passed':all(r['passed'] for r in results),
            'excluded':['test_modelo_final.FinalPost: 8 verificações de cache de 2025 preservadas, não executadas nesta regressão'],
            'new_training':False,'new_2025_predictions':False,
            'scope':'Testes históricos de integridade podem ler metadados/rótulos de 2025; sem novas métricas ou modelos nesse ano.'}
    (OUT/'testes_regressao.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':run()
