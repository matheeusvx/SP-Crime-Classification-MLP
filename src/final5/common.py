from ml.runtime import ROOT,FEATURES,json_write,sha256
import json,csv,datetime
OUT=ROOT/'reports/etapa5'
FINAL=ROOT/'models/final'
MODEL_ID='gs-celulares-sp-dense64-v1.0.0'

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
def save(name,rows):
    if not rows:return
    with (OUT/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def preserve():
    p=OUT/'preservacao.json'
    if not p.exists():
        paths=[]
        excluded_names={'test_modelo_final.py','protocolo_teste_final.md','contrato_inferencia.md','decisao_modelo_final.md','recomendacoes_etapa6.md'}
        for directory in ['data','models','reports','docs','notebooks','src','tests']:
            paths.extend(x for x in (ROOT/directory).rglob('*') if x.is_file() and '__pycache__' not in x.parts and 'tmp' not in x.parts
              and 'final5' not in x.parts and 'etapa5' not in x.parts and 'final' not in x.parts and 'etapa5' not in x.name
              and not x.name.startswith('05_') and x.name not in excluded_names)
        paths.extend(ROOT/n for n in ['README.md','requirements.txt','requirements-ml.txt','.gitignore','docs/recomendacoes_etapa5.md'])
        json_write(p,{x.relative_to(ROOT).as_posix():sha256(x) for x in set(paths)})
    changed=[p for p,h in read('preservacao.json').items() if sha256(ROOT/p)!=h]
    if changed:raise RuntimeError(f'Historico alterado: {changed}')
    return len(read('preservacao.json'))

def verify_manifest(folder=FINAL):
    m=json.loads((folder/'manifesto.json').read_text(encoding='utf-8'))
    for name,h in m['frozen_files'].items():
        path=folder/name
        if not path.exists() or sha256(path)!=h:raise RuntimeError('Artefato final alterado: '+name)
    for name,h in m['inference_source_hashes'].items():
        if sha256(ROOT/name)!=h:raise RuntimeError('Codigo de inferencia alterado: '+name)
    if sha256(folder/'manifesto.json')!=(folder/'manifesto.sha256').read_text().strip():raise RuntimeError('Manifesto de congelamento alterado')
    return m
