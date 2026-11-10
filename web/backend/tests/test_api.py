"""Testes HTTP com o modelo real; somente entradas sintéticas, sem dados de 2025."""
import json
import math
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import REPO_ROOT, Settings
from app.inference import load_model_service
from app.main import create_app

MODELO = 'gs-celulares-sp-dense64-v1.0.0'
DATA = REPO_ROOT/'web/backend/data'


def post(client, body):
    return client.post('/api/classify', json=body)


def app_sem_modelo(**kwargs):
    def falha():
        raise RuntimeError('artefato ausente em /caminho/interno')
    return create_app(Settings(**kwargs), service_factory=falha)


# ---- Carregamento e integridade


def test_health_ok(client):
    r = client.get('/api/health')
    assert r.status_code == 200
    assert r.json() == {'status': 'ok', 'modelo_carregado': True, 'estatisticas_carregadas': True, 'versao_api': '1.0.0'}


def test_modelo_correto_carregado(service):
    pipeline = service._classifier._pipeline
    assert pipeline.manifest['model_id'] == MODELO
    assert pipeline.model.count_params() == 19265
    assert pipeline.model.input_shape[-1] == 299
    assert pipeline.manifest['threshold'] == 0.5
    assert pipeline.calibrator is None


def test_modelo_carregado_uma_unica_vez(service, valido):
    fabrica = patch('final5.pipeline.FinalPipeline.__init__', side_effect=AssertionError('recarga indevida'))
    with fabrica, TestClient(create_app(Settings(), service_factory=lambda: service)) as c:
        for _ in range(3):
            assert post(c, valido).status_code == 200


def test_artefato_adulterado_impede_classificacao(tmp_path, valido):
    copia = tmp_path/'final'
    shutil.copytree(REPO_ROOT/'models/final', copia)
    with (copia/'modelo.keras').open('ab') as f:
        f.write(b'\0')
    app = create_app(Settings(model_dir=copia))
    with TestClient(app) as c:
        assert c.get('/api/health').status_code == 503
        r = post(c, valido)
        assert r.status_code == 503
        assert r.json()['status'] == 'servico_indisponivel'
        assert 'classe_estimada' not in r.json()


def test_artefato_ausente_impede_carga(tmp_path):
    with pytest.raises(Exception):
        load_model_service(tmp_path)


def test_modelo_indisponivel_sem_resposta_ficticia(valido):
    with TestClient(app_sem_modelo()) as c:
        for r in (post(c, valido), c.get('/api/options'), c.get('/api/model')):
            assert r.status_code == 503
            assert r.json()['status'] == 'servico_indisponivel'
            assert 'scores_sigmoid' not in r.json()
            assert '/caminho/interno' not in r.text
        h = c.get('/api/health')
        assert h.status_code == 503 and h.json()['modelo_carregado'] is False
        # Agregados não dependem do modelo.
        assert c.get('/api/statistics').status_code == 200


def test_falha_na_inferencia_nao_vaza_detalhes(service, valido):
    with patch.object(service, 'classify', side_effect=RuntimeError('segredo /interno')):
        with TestClient(create_app(Settings(), service_factory=lambda: service)) as c:
            r = post(c, valido)
    assert r.status_code == 503 and 'segredo' not in r.text


# ---- Contrato válido


def test_contrato_sucesso(client, valido):
    r = post(client, valido)
    assert r.status_code == 200
    b = r.json()
    assert set(b) == {'status', 'classe_estimada', 'codigo_classe', 'scores_sigmoid', 'versao_modelo', 'versao_contrato',
                      'probabilidades_calibradas', 'avisos', 'erros', 'grupos', 'interpretacao_scores'}
    assert b['status'] == 'ok' and b['versao_modelo'] == MODELO and b['versao_contrato'] == '1.1.0'
    assert b['probabilidades_calibradas'] is False and b['erros'] == []
    s = b['scores_sigmoid']
    assert math.isclose(s['furto']+s['roubo'], 1, abs_tol=1e-6)
    assert b['codigo_classe'] == int(s['roubo'] >= 0.5)
    assert b['classe_estimada'] == ('ROUBO' if b['codigo_classe'] else 'FURTO')


@pytest.mark.parametrize('entrada', [
    {'mes': 1, 'dia_semana': 0, 'tipo_local': 'VIA PÚBLICA', 'bairro': 'CENTRO'},
    {'mes': 12, 'dia_semana': 6, 'tipo_local': 'RESIDÊNCIA', 'bairro': 'MOOCA'},
    {'mes': 7, 'dia_semana': 4, 'tipo_local': 'OUTROS', 'bairro': 'LAPA'},
    {'mes': 3, 'dia_semana': 1, 'tipo_local': None, 'bairro': 'SANTANA'},
    {'mes': 3, 'dia_semana': 1, 'tipo_local': 'TERMINAL/ESTAÇÃO', 'bairro': None},
])
def test_http_equivale_a_interface_python_segura(client, service, entrada):
    r = post(client, entrada)
    assert r.status_code == 200
    assert r.json() == json.loads(json.dumps(service.classify(entrada)))


def test_resposta_deterministica(client, valido):
    assert post(client, valido).json() == post(client, valido).json()


# ---- Validação bloqueante


@pytest.mark.parametrize('campo,valor,codigo', [
    ('mes', None, 'dominio_invalido'), ('mes', 0, 'dominio_invalido'), ('mes', 13, 'dominio_invalido'),
    ('mes', '5', 'dominio_invalido'), ('mes', 5.0, 'dominio_invalido'), ('mes', True, 'dominio_invalido'),
    ('dia_semana', None, 'dominio_invalido'), ('dia_semana', 7, 'dominio_invalido'),
    ('dia_semana', '2', 'dominio_invalido'), ('dia_semana', -1, 'dominio_invalido'),
    ('tipo_local', 'PRAIA', 'categoria_desconhecida'), ('tipo_local', 123, 'categoria_invalida'),
    ('tipo_local', '__AUSENTE__', 'categoria_invalida'),
    ('bairro', 'BAIRRO NUNCA OBSERVADO XYZ', 'categoria_desconhecida'),
    ('bairro', '123', 'categoria_invalida'), ('bairro', '', 'categoria_invalida'),
])
def test_rejeicao_sem_inferencia(client, service, valido, campo, valor, codigo):
    with patch.object(service._classifier._pipeline, 'classificar', side_effect=AssertionError('inferência indevida')):
        r = post(client, valido | {campo: valor})
    assert r.status_code == 422
    b = r.json()
    assert b['status'] == 'erro_validacao'
    assert 'classe_estimada' not in b and 'scores_sigmoid' not in b
    assert any(e['campo'] == campo and e['codigo'] == codigo for e in b['erros'])


@pytest.mark.parametrize('corpo', ['{"mes":NaN,"dia_semana":2,"tipo_local":null,"bairro":null}',
                                   '{"mes":Infinity,"dia_semana":2,"tipo_local":null,"bairro":null}'])
def test_nan_e_infinito_rejeitados(client, corpo):
    r = client.post('/api/classify', content=corpo, headers={'Content-Type': 'application/json'})
    assert r.status_code == 422 and r.json()['status'] == 'erro_validacao'


@pytest.mark.parametrize('corpo', [{}, {'mes': 5}, [1, 2], 'texto'])
def test_esquema_incompleto(client, corpo):
    r = post(client, corpo)
    assert r.status_code == 422
    assert r.json()['erros'][0]['codigo'] == 'esquema_invalido'


def test_atributos_extras_rejeitados(client, valido):
    r = post(client, valido | {'natureza': 'ROUBO'})
    assert r.status_code == 422 and r.json()['erros'][0]['codigo'] == 'esquema_invalido'


def test_json_malformado(client):
    r = client.post('/api/classify', content='{mes:', headers={'Content-Type': 'application/json'})
    assert r.status_code == 422 and r.json()['erros'][0]['codigo'] == 'esquema_invalido'
    assert '{mes:' not in r.text


def test_corpo_nao_utf8_segue_o_contrato(client):
    corpo = '{"mes":5,"bairro":"Ú"}'.encode('latin-1')
    r = client.post('/api/classify', content=corpo, headers={'Content-Type': 'application/json'})
    assert r.status_code == 422 and r.json()['erros'][0]['codigo'] == 'esquema_invalido'


def test_mensagens_nao_ecoam_entrada(client, valido):
    r = post(client, valido | {'bairro': 'RUA DO FULANO DE TAL 123'})
    assert r.status_code == 422 and 'FULANO' not in r.text


# ---- Avisos e grupos


def _raro(service):
    return next(b['valor'] for b in service.options()['bairros'] if b['grupo'] == 'raro')


def test_bairro_raro_tem_aviso(client, service, valido):
    b = post(client, valido | {'bairro': _raro(service)}).json()
    assert b['status'] == 'ok' and b['grupos']['bairro'] == 'raro'
    assert any(a['codigo'] == 'bairro_raro' for a in b['avisos'])


def test_ausencia_explicita_tem_aviso(client, valido):
    b = post(client, valido | {'tipo_local': None, 'bairro': None}).json()
    assert b['status'] == 'ok'
    assert {a['campo'] for a in b['avisos'] if a['codigo'] == 'ausente'} == {'tipo_local', 'bairro'}
    assert b['grupos'] == {'tipo_local': 'ausente', 'bairro': 'ausente'}


def test_bairro_frequente_sem_aviso(client, valido):
    assert post(client, valido).json()['avisos'] == []


# ---- Opções e metadados


def test_opcoes_vem_do_vocabulario(client, service):
    r = client.get('/api/options')
    assert r.status_code == 200
    b = r.json()
    v = service._classifier.validator.vocabulary()
    assert [m['valor'] for m in b['meses']] == list(range(1, 13))
    assert [(d['valor'], d['rotulo']) for d in b['dias_semana']][0] == (0, 'Segunda-feira')
    assert b['dias_semana'][6] == {'valor': 6, 'rotulo': 'Domingo'}
    assert b['tipos_local'] == v['tipo_local'] and b['bairros'] == v['bairro']
    assert '__AUSENTE__' not in b['tipos_local']
    assert not {'__AUSENTE__', '__BAIRRO_RARO__'} & {x['valor'] for x in b['bairros']}


def test_opcoes_tem_exemplos_de_treinamento(client, service):
    """Nenhuma opção ativa pesos sem exemplos: todas foram observadas em 2023."""
    pre = service._classifier.validator.preprocessor
    b = client.get('/api/options').json()
    assert all(pre.counts['tipo_local'].get(x, 0) > 0 for x in b['tipos_local'])
    assert all(pre.counts['bairro'].get(x['valor'], 0) > 0 for x in b['bairros'])


def test_todas_as_opcoes_de_local_sao_aceitas(client, valido):
    for local in client.get('/api/options').json()['tipos_local']:
        assert post(client, valido | {'tipo_local': local}).status_code == 200


def test_metadados_publicos(client):
    r = client.get('/api/model')
    assert r.status_code == 200
    b = r.json()
    assert b['versao_modelo'] == MODELO and b['limiar'] == 0.5 and b['probabilidades_calibradas'] is False
    assert b['arquitetura'] == {'entradas': 299, 'camadas_ocultas': [64], 'ativacoes': ['relu', 'sigmoid'],
                                'parametros_treinaveis': 19265}
    assert sum(b['colunas_por_atributo'].values()) == 299
    assert 'sha256' not in r.text.lower() and 'models/' not in r.text and 'hash' not in r.text.lower()


# ---- Estatísticas e dados sensíveis


def test_estatisticas_conferem_com_base(client):
    b = client.get('/api/statistics').json()
    assert b['total'] == {'furtos': 298083, 'roubos': 207104}
    assert sum(a['furtos']+a['roubos'] for a in b['por_ano']) == 505187
    assert sum(m['furtos'] for m in b['por_mes']) == 298083
    assert sum(m['roubos'] for m in b['por_mes']) == 207104
    assert len(b['por_mes']) == 36
    assert len(b['por_dia_mes']) == 36*7
    assert sum(d['furtos'] for d in b['por_dia_mes']) == 298083
    assert sum(d['roubos'] for d in b['por_dia_mes']) == 207104
    for ano in b['por_tipo_local']:
        linha = next(a for a in b['por_ano'] if a['ano'] == ano['ano'])
        assert sum(c['furtos'] for c in ano['categorias']) == linha['furtos']
        assert sum(c['roubos'] for c in ano['categorias']) == linha['roubos']


def test_estatisticas_conferem_com_tabelas_da_etapa1(client):
    import csv
    with (REPO_ROOT/'reports/tables/classes_por_ano.csv').open(encoding='utf-8-sig') as f:
        linhas = list(csv.DictReader(f))
    b = client.get('/api/statistics').json()
    for a in b['por_ano']:
        for alvo, chave in (('0', 'furtos'), ('1', 'roubos')):
            esperado = next(int(x['boletins']) for x in linhas if x['ano_fato'] == str(a['ano']) and x['alvo'] == alvo)
            assert a[chave] == esperado


def test_ausente_e_outros_identificados(client):
    cats = client.get('/api/statistics').json()['por_tipo_local'][0]['categorias']
    assert {c['tipo'] for c in cats} >= {'ausente', 'outros'}


def test_agregados_sem_campos_sensiveis():
    texto = (DATA/'estatisticas.json').read_text(encoding='utf-8').lower()
    for proibido in ['bairro', 'chave_bo', 'delegacia', 'logradouro', 'latitude', 'longitude', 'cpf', 'data_fato']:
        assert proibido not in texto
    json.loads(texto)


def test_metodologia_reproduz_metricas_publicadas(client):
    m = client.get('/api/methodology').json()
    t = m['desempenho']['teste_2025']
    assert round(t['accuracy']*100, 2) == 68.82 and round(t['macro_f1']*100, 2) == 67.09
    assert round(t['precision_roubo']*100, 2) == 56.15 and round(t['recall_roubo']*100, 2) == 63.42
    assert round(t['balanced_accuracy']*100, 2) == 67.65 and t['auc'] == 0.7412
    assert round(t['ece10']*100, 2) == 8.10
    assert (t['tn'], t['fp'], t['fn'], t['tp']) == (71598, 28009, 20691, 35870)
    assert m['grupos_2025']['tipo_local']['VIA PÚBLICA']['n'] == 122014
    assert sum(g['n'] for g in m['grupos_2025']['condicao_bairro'].values()) == 156168
    assert [a['nome'] for a in m['arquiteturas']] == ['Dense32', 'Dense64', 'Dense64 → Dense32']
    assert m['referencias_2025']['tabela_frequencias']['accuracy'] == pytest.approx(.6928)
    assert m['referencias_2025']['classe_majoritaria']['accuracy'] == pytest.approx(.6378195, abs=1e-6)


@pytest.mark.parametrize('rota', ['/data/processed/base_modelagem.parquet', '/models/final/modelo.keras',
                                  '/models/final/manifesto.json', '/api/data', '/api/train', '/web/backend/data/estatisticas.json',
                                  '/assets/../../models/final/manifesto.json', '/.env', '/reports/auditoria_claude.md'])
def test_sem_acesso_a_arquivos_internos(client, rota):
    assert client.get(rota).status_code == 404


def test_sem_endpoint_de_treino():
    rotas = {r.path for r in create_app(Settings(app_env='production'), service_factory=lambda: None).routes}
    assert not [r for r in rotas if any(x in r for x in ['train', 'treino', 'upload', 'retrain'])]


def test_estatisticas_indisponiveis(tmp_path, service):
    app = create_app(Settings(data_dir=tmp_path), service_factory=lambda: service)
    with TestClient(app) as c:
        assert c.get('/api/statistics').status_code == 503
        assert c.get('/api/methodology').status_code == 503


def test_agregado_com_campo_extra_e_recusado(tmp_path, service):
    bruto = json.loads((DATA/'estatisticas.json').read_text(encoding='utf-8'))
    bruto['boletins'] = [{'bairro': 'X'}]
    (tmp_path/'estatisticas.json').write_text(json.dumps(bruto), encoding='utf-8')
    with TestClient(create_app(Settings(data_dir=tmp_path), service_factory=lambda: service)) as c:
        assert c.get('/api/statistics').status_code == 503


# ---- Segurança HTTP


def test_cors_restritivo(client):
    origem = {'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'}
    assert client.options('/api/classify', headers=origem).headers['access-control-allow-origin'] == 'http://localhost:5173'
    r = client.options('/api/classify', headers=origem | {'Origin': 'https://site-nao-autorizado.example'})
    assert 'access-control-allow-origin' not in r.headers


def test_cors_recusa_curinga(monkeypatch):
    from app.config import load_settings
    monkeypatch.setenv('CORS_ORIGINS', '*')
    with pytest.raises(ValueError):
        load_settings()


def test_cabecalhos_de_seguranca(client):
    h = client.get('/api/health').headers
    assert h['x-content-type-options'] == 'nosniff' and 'content-security-policy' in h


def test_corpo_grande_rejeitado(client, valido):
    r = post(client, valido | {'bairro': 'A'*5000})
    assert r.status_code == 413 and r.json()['status'] == 'requisicao_grande'


def test_limite_de_requisicoes(service, valido):
    with TestClient(create_app(Settings(rate_limit_per_minute=2), service_factory=lambda: service)) as c:
        assert post(c, valido).status_code == 200
        assert post(c, valido).status_code == 200
        r = post(c, valido)
    assert r.status_code == 429 and int(r.headers['retry-after']) >= 1
    assert r.json()['status'] == 'limite_excedido'


def test_docs_desativados_em_producao(service):
    with TestClient(create_app(Settings(app_env='production'), service_factory=lambda: service)) as c:
        assert c.get('/api/docs').status_code == 404
        assert c.get('/api/openapi.json').status_code == 404


def test_entrada_nao_vai_para_logs(client, valido, caplog):
    with caplog.at_level('DEBUG'):
        post(client, valido | {'bairro': 'MARCADOR-PRIVADO'})
    assert 'MARCADOR-PRIVADO' not in caplog.text


def test_serve_somente_build(tmp_path, service):
    dist = tmp_path/'dist'
    (dist/'assets').mkdir(parents=True)
    (dist/'index.html').write_text('<html>app</html>', encoding='utf-8')
    (dist/'assets'/'a.js').write_text('1', encoding='utf-8')
    (tmp_path/'segredo.txt').write_text('x', encoding='utf-8')
    with TestClient(create_app(Settings(frontend_dist=dist), service_factory=lambda: service)) as c:
        for rota in ['/', '/painel', '/sobre']:
            assert c.get(rota).status_code == 200
        assert c.get('/assets/a.js').status_code == 200
        assert c.get('/assets/../segredo.txt').status_code == 404
        assert c.get('/index.html').status_code == 404
        assert c.get('/nao-existe').status_code == 404


def test_codigo_nao_usa_execucao_dinamica():
    fontes = Path(REPO_ROOT/'web/backend/app').glob('*.py')
    for f in fontes:
        t = f.read_text(encoding='utf-8')
        assert 'eval(' not in t and 'exec(' not in t and 'FinalPipeline' not in t and 'ml.inference' not in t
