"""Inicializacao local sem alterar as dependencias nem artefatos da Etapa 1."""
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
for p in [ROOT/'.runtime',ROOT/'.runtime_ml',ROOT/'src']:
    if p.exists(): sys.path.insert(0,str(p))
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL','2')
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS','0')
os.environ.setdefault('TF_DETERMINISTIC_OPS','1')
os.environ.setdefault('OMP_NUM_THREADS','4')
FEATURES=['mes','dia_semana','tipo_local','bairro']
LABELS={0:'FURTO',1:'ROUBO'}
OUT=ROOT/'reports/etapa2'
MODELS=ROOT/'models'

def configure_tf(seed=42):
    import tensorflow as tf
    tf.config.threading.set_inter_op_parallelism_threads(1)
    tf.config.threading.set_intra_op_parallelism_threads(4)
    tf.keras.utils.set_random_seed(seed)
    tf.config.experimental.enable_op_determinism()
    return tf

def json_write(path,value):
    import json
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def sha256(path):
    import hashlib
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def stage1_snapshot():
    paths=[]
    for folder in ['data/processed','data/interim','src/data','docs','notebooks','reports','tests']:
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'tmp' not in p.parts
          and 'etapa2' not in p.parts and not (folder=='docs' and p.name!='decisoes.md')
          and not (folder=='notebooks' and p.name!='01_auditoria_exploracao.ipynb')
          and not (folder=='tests' and p.name!='test_integridade.py')
          and 'etapa2' not in p.name and '_baseline' not in p.name)
    paths.extend(ROOT/p for p in ['README.md','requirements.txt'])
    return {p.relative_to(ROOT).as_posix():sha256(p) for p in sorted(set(paths))}
