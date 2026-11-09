"""Registra apenas o conjunto explícito de revisões autorizadas na Etapa 5.6.

Executar após revisar o diff. Recusa qualquer alteração fora desta lista;
não atualiza manifestos de ML e nunca acessa dados para inferência.
"""
from ml.runtime import ROOT, sha256
from maintenance56.integrity import OUT, SNAPSHOT
import json
from datetime import datetime, timezone

REASONS = {
    '.gitignore': 'Exclusões recursivas para dados privados, binários, segredos e caches.',
    'README.md': 'Estado atual, contrato seguro, limitações, teste consumido e rastreabilidade.',
    'src/ml/inference.py': 'Marcação de legado histórico sem mudança do comportamento.',
    'tests/test_ml_pipeline.py': 'Preservação valida original no snapshot e revisão autorizada.',
    'tests/test_robustez_ml.py': 'Escopo histórico do teste de acentuação e preservação revisada.',
    'tests/test_experimentos_ml.py': 'Preservação valida original e revisão sem reescrever manifesto.',
    'tests/test_modelo_final.py': 'Preservação histórica com revisão explícita; FinalPost separado.',
    'docs/decisao_modelo_final.md': 'Errata de calibração, referência retrospectiva e independência.',
    'docs/contrato_inferencia.md': 'Contrato histórico identificado; encaminhamento ao seguro.',
    'docs/protocolo_teste_final.md': 'Ressalvas de teste consumido e distinção calibração/limiar.',
    'docs/recomendacoes_etapa6.md': 'Orientação ao adaptador seguro e campos controlados.',
    'reports/relatorio_etapa5.md': 'Errata separada sem substituir métricas publicadas.',
    'notebooks/05_avaliacao_final.ipynb': 'Célula de errata; código e saídas históricos inalterados.',
}


def register():
    original=json.loads((OUT/'estado_anterior.json').read_text(encoding='utf-8'))['files']
    changes={}
    for name, before in original.items():
        after=sha256(ROOT/name)
        if before != after:
            if name not in REASONS: raise RuntimeError('Alteração não autorizada: '+name)
            changes[name]={'before_sha256':before,'after_sha256':after,'reason':REASONS[name]}
    value={'revision':'pos-auditoria-1.0.0','created_at':datetime.now(timezone.utc).isoformat(),
           'snapshot_tag':SNAPSHOT,'retroactive_evidence':False,'files':changes}
    (OUT/'revisoes_autorizadas.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(changes)} revisões explícitas; {len(original)-len(changes)} arquivos originais sem alteração.')


if __name__=='__main__':register()
