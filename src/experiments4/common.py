from ml.runtime import ROOT,FEATURES,json_write,sha256
import csv,json
from pathlib import Path
OUT=ROOT/'reports/etapa4'
MODELS=ROOT/'models/experiments/etapa4'
PLAN_VERSION=1

def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
def save(name,rows):
    if not rows:return
    p=OUT/(name+'.csv');p.parent.mkdir(parents=True,exist_ok=True)
    cols=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
def preserve():
    p=OUT/'preservacao.json'
    if not p.exists():
        paths=[]
        for directory in ['data','models','reports','docs','notebooks','src/data','src/ml','src/diagnostics','tests']:
            paths.extend(x for x in (ROOT/directory).rglob('*') if x.is_file() and '__pycache__' not in x.parts and 'tmp' not in x.parts
              and 'etapa4' not in x.parts and 'etapa4' not in x.name and 'etapa5' not in x.name and not x.name.startswith('04_') and x.name!='test_experimentos_ml.py')
        paths.extend(ROOT/n for n in ['README.md','requirements.txt','requirements-ml.txt','.gitignore','docs/recomendacoes_etapa4.md'])
        json_write(p,{x.relative_to(ROOT).as_posix():sha256(x) for x in paths})
    changed=[name for name,h in read('preservacao.json').items() if sha256(ROOT/name)!=h]
    if changed:raise RuntimeError(f'Arquivos anteriores modificados: {changed}')
    return len(read('preservacao.json'))

def data(year):
    if year not in (2023,2024):raise ValueError('Somente 2023/2024 autorizados; 2025 bloqueado')
    from ml.dataset import connection,load_year
    c=connection();records,y,keys=load_year(c,year)
    missing=c.sql(f'''SELECT count(*) FROM indexed b JOIN meta m USING(indice_linha) JOIN analytic a USING(chave_bo)
      WHERE year(m.data_fato)={year} AND (b.mes IS DISTINCT FROM a.mes OR b.dia_semana IS DISTINCT FROM a.dia_semana
      OR b.tipo_local IS DISTINCT FROM a.tipo_local OR b.bairro IS DISTINCT FROM a.bairro OR b.alvo IS DISTINCT FROM a.alvo
      OR m.data_fato IS DISTINCT FROM a.data_fato OR b.mes!=month(m.data_fato))''').fetchall()[0][0]
    c.close()
    if missing or len(keys)!=len(set(keys)):raise ValueError('Alinhamento ou unicidade invalida')
    return records,y,keys
