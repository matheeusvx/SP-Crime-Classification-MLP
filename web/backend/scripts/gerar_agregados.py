"""Gera os JSON públicos da Etapa 6 a partir de resultados já existentes.

Uso: python web/backend/scripts/gerar_agregados.py

Só conta registros elegíveis e copia métricas publicadas. Não carrega o modelo,
não executa inferência e não calcula nenhuma métrica nova de classificação.
A saída é determinística e não contém boletins, bairros ou identificadores.
"""
import csv
import hashlib
import json
from pathlib import Path
import re

import duckdb

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'web/backend/data'
PROVENIENCIA = ROOT/'reports/etapa6/proveniencia_agregados.json'
ELEGIVEIS = ROOT/'data/processed/ocorrencias_elegiveis.parquet'
FONTES_METRICAS = {
    'comparacao': ROOT/'reports/etapa4/comparacao_arquiteturas.csv',
    'resumo': ROOT/'reports/etapa4/resumo_validacao_2024.csv',
    'teste': ROOT/'reports/etapa5/metricas_2025.json',
    'validacao': ROOT/'reports/etapa5/metricas_2024_pipeline_final.json',
    'majoritaria': ROOT/'reports/etapa5/referencia_majoritaria_2025.json',
    'grupos': ROOT/'reports/etapa5/metricas_grupos_2025.csv',
    'auditoria': ROOT/'reports/auditoria_claude.md',
    'manifesto': ROOT/'models/final/manifesto.json',
}
FONTE_URL = 'https://www.ssp.sp.gov.br/estatistica/consultas'
# Categorias com menos boletins que isto nos três anos entram em "Demais categorias".
LIMIAR_DEMAIS = 1000
AUSENTE, DEMAIS = 'Não informado', 'Demais categorias'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contar(rows):
    return {'furtos': int(rows.get(0, 0)), 'roubos': int(rows.get(1, 0))}


def estatisticas():
    if not ELEGIVEIS.exists():
        raise SystemExit(f'Base processada ausente: {ELEGIVEIS.relative_to(ROOT)}')
    db = duckdb.connect()
    db.execute(f"""CREATE VIEW e AS SELECT ano_fato ano, month(data_fato) mes, dia_semana dia, alvo,
                   NULLIF(TRIM(tipo_local), '') local
                   FROM read_parquet('{ELEGIVEIS.as_posix()}')""")
    por = lambda sql: db.sql(sql).fetchall()
    total = dict(por('SELECT alvo, count(*) FROM e GROUP BY alvo'))
    anos = {}
    for ano, alvo, n in por('SELECT ano, alvo, count(*) FROM e GROUP BY ALL'):
        anos.setdefault(ano, {})[alvo] = n
    meses = {}
    for ano, mes, alvo, n in por('SELECT ano, mes, alvo, count(*) FROM e GROUP BY ALL'):
        meses.setdefault((ano, mes), {})[alvo] = n
    dias = {}
    for ano, mes, dia, alvo, n in por('SELECT ano, mes, dia, alvo, count(*) FROM e GROUP BY ALL'):
        dias.setdefault((ano, mes, dia), {})[alvo] = n
    volume = dict(por('SELECT local, count(*) FROM e WHERE local IS NOT NULL GROUP BY local'))

    def rotulo(local):
        if local is None:
            return AUSENTE, 'ausente'
        if local == 'OUTROS':
            return 'OUTROS', 'outros'
        if volume[local] < LIMIAR_DEMAIS:
            return DEMAIS, 'demais'
        return local, 'categoria'
    locais = {}
    for ano, local, alvo, n in por('SELECT ano, local, alvo, count(*) FROM e GROUP BY ALL'):
        nome, tipo = rotulo(local)
        item = locais.setdefault(ano, {}).setdefault((nome, tipo), {})
        item[alvo] = item.get(alvo, 0)+n
    return {
        'fonte': {'nome': 'Secretaria da Segurança Pública do Estado de São Paulo (SSP-SP) — Celulares subtraídos',
                  'url': FONTE_URL,
                  'recorte': 'Boletins elegíveis de furto e roubo de celulares no município de São Paulo, por ano do fato.'},
        'periodo': {'inicio': '2023-01', 'fim': '2025-12'},
        'total': contar(total),
        'por_ano': [{'ano': a, **contar(anos[a])} for a in sorted(anos)],
        'por_mes': [{'ano': a, 'mes': m, **contar(meses[(a, m)])} for a, m in sorted(meses)],
        'por_dia_mes': [{'ano': a, 'mes': m, 'dia_semana': d, **contar(dias[(a, m, d)])} for a, m, d in sorted(dias)],
        'por_tipo_local': [{'ano': a, 'categorias': sorted(
            ({'categoria': n, 'tipo': t, **contar(v)} for (n, t), v in locais[a].items()),
            key=lambda c: (c['tipo'] == 'demais', -(c['furtos']+c['roubos']), c['categoria']))}
            for a in sorted(locais)],
        'limiar_demais_categorias': LIMIAR_DEMAIS,
    }


def csv_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def numero_br(texto):
    return float(texto.replace('%', '').replace(' ', '').replace(',', '.'))


def fracao(texto):
    return round(numero_br(texto)/100, 6)


def auditoria():
    """Lê as tabelas A1 e M4 do próprio relatório, evitando transcrição manual."""
    md = FONTES_METRICAS['auditoria'].read_text(encoding='utf-8')
    saida = {}
    linha = r'\| (2024|2025) \| (Tabela de frequências|MLP Dense64) \| ([\d,]+) % \| ([\d,]+) % \| ([\d,]+) % \| ([\d,]+) \| ([\d,]+) \|'
    for ano, nome, acc, f1, rec, auc, brier in re.findall(linha, md):
        chave = 'tabela_frequencias' if nome.startswith('Tabela') else 'mlp'
        saida.setdefault(ano, {})[chave] = {
            'accuracy': fracao(acc), 'macro_f1': fracao(f1), 'recall_roubo': fracao(rec),
            'auc': numero_br(auc), 'brier': numero_br(brier)}
    if set(saida) != {'2024', '2025'}:
        raise SystemExit('Tabela A1 da auditoria não encontrada.')
    prev = re.search(r'\| Prevalência de roubo \| ([\d,]+) % \| ([\d,]+) % \| ([\d,]+) % \|', md)
    medio = re.search(r'\| Probabilidade média prevista \| ([\d,]+) % \| ([\d,]+) % \| ([\d,]+) % \|', md)
    if not prev or not medio:
        raise SystemExit('Tabela M4 da auditoria não encontrada.')
    anos = ['2023', '2024', '2025']
    return saida, [{'ano': int(a), 'prevalencia_roubo': fracao(prev[i+1]),
                    'score_medio_roubo': fracao(medio[i+1])} for i, a in enumerate(anos)]


def metricas(m):
    campos = ['n', 'furtos', 'roubos', 'tn', 'fp', 'fn', 'tp', 'accuracy', 'macro_f1', 'balanced_accuracy',
              'precision_roubo', 'recall_roubo', 'f1_roubo', 'precision_furto', 'recall_furto', 'f1_furto',
              'brier', 'log_loss', 'ece10']
    return {c: m[c] for c in campos}


def metodologia():
    comparacao = {r['id']: r for r in csv_rows(FONTES_METRICAS['comparacao'])}
    resumo = {r['id']: r for r in csv_rows(FONTES_METRICAS['resumo'])}
    nomes = {'B32': 'Dense32', 'B64': 'Dense64', 'B64_32': 'Dense64 → Dense32'}
    arquiteturas = []
    for chave, nome in nomes.items():
        c, r = comparacao[chave], resumo[chave]
        arquiteturas.append({
            'id': chave, 'nome': nome, 'camadas': c['architecture'], 'parametros': int(c['parameters']),
            'semente_42': {k: float(c[k]) for k in ['accuracy', 'macro_f1', 'balanced_accuracy', 'precision_roubo',
                                                    'recall_roubo', 'brier', 'log_loss']},
            'n_sementes': int(r['n_seeds']), 'sementes': r['seeds'],
            'macro_f1_media': float(r['macro_f1_mean']),
            'macro_f1_dp': float(r['macro_f1_sd']) if r['macro_f1_sd'] else None,
            'recall_roubo_media': float(r['recall_roubo_mean']),
        })
    ler = lambda chave: json.loads(FONTES_METRICAS[chave].read_text(encoding='utf-8'))
    manifesto = ler('manifesto')
    teste, validacao = ler('teste'), ler('validacao')
    a1, nivel = auditoria()
    maj = ler('majoritaria')['metrics']
    grupos = {}
    for r in csv_rows(FONTES_METRICAS['grupos']):
        if r['grupo'] in ('tipo_local', 'condicao_bairro'):
            grupos.setdefault(r['grupo'], {})[r['categoria']] = {
                'n': int(r['n']), 'accuracy': float(r['accuracy']), 'fp': int(r['fp']), 'fn': int(r['fn'])}
    return {
        'grupos_2025': grupos,
        'conjuntos': [
            {'papel': 'Treino', 'ano': 2023, 'boletins': manifesto['preprocessing']['fit_rows']},
            {'papel': 'Validação (desenvolvimento)', 'ano': 2024, 'boletins': validacao['n']},
            {'papel': 'Teste final', 'ano': 2025, 'boletins': teste['n']},
        ],
        'arquiteturas': arquiteturas,
        'desempenho': {'validacao_2024': {**metricas(validacao), 'auc': a1['2024']['mlp']['auc']},
                       'teste_2025': {**metricas(teste), 'auc': a1['2025']['mlp']['auc']}},
        'referencias_2025': {
            'classe_majoritaria': {'accuracy': maj['accuracy'], 'macro_f1': maj['macro_f1'],
                                   'balanced_accuracy': maj['balanced_accuracy']},
            'tabela_frequencias': a1['2025']['tabela_frequencias'],
            'mlp': a1['2025']['mlp'],
        },
        'referencias_2024': {'tabela_frequencias': a1['2024']['tabela_frequencias'], 'mlp': a1['2024']['mlp']},
        'nivel_scores': nivel,
    }


def gravar(path, valor):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(valor, ensure_ascii=False, indent=1)+'\n', encoding='utf-8', newline='\n')


def main():
    gravar(OUT/'estatisticas.json', estatisticas())
    gravar(OUT/'metodologia.json', metodologia())
    entradas = {ELEGIVEIS.relative_to(ROOT).as_posix(): sha256(ELEGIVEIS)}
    entradas |= {p.relative_to(ROOT).as_posix(): sha256(p) for p in FONTES_METRICAS.values()}
    gravar(PROVENIENCIA, {
        'script': 'web/backend/scripts/gerar_agregados.py', 'entradas_sha256': entradas,
        'saidas_sha256': {p: sha256(OUT/p) for p in ['estatisticas.json', 'metodologia.json']},
        'inferencia_executada': False, 'treinamento_executado': False,
        'observacao': 'Contagens descritivas e cópia de métricas publicadas; 2025 não foi usado para ajustar modelo.'})
    print('Agregados gerados em', OUT.relative_to(ROOT))


if __name__ == '__main__':
    main()
