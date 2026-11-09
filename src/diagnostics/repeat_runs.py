from diagnostics.common import *
import subprocess,sys,os
if __name__=='__main__':
    preserve()
    for seed in [42,7,123]:
        env=os.environ.copy();env['PYTHONPATH']=str(ROOT/'src');env['PYTHONHASHSEED']='42'
        subprocess.run([sys.executable,'-m','diagnostics.stability','--seed',str(seed)],cwd=ROOT,env=env,check=True)
    results=[read(f'estabilidade_{seed}.json') for seed in [42,7,123]]
    save('estabilidade_sementes',[{k:v for k,v in r.items() if k not in ['config','history']} for r in results])
    json_write(OUT/'estabilidade_resumo.json',{k:{'min':min(r[k] for r in results),'max':max(r[k] for r in results),'media':float(np.mean([r[k] for r in results])),'dp_amostral':float(np.std([r[k] for r in results],ddof=1))} for k in ['accuracy','macro_f1','balanced_accuracy','recall_roubo']})
