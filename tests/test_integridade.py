"""Verificacoes independentes dos artefatos e dos vinculos com a fonte."""
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/data'))
from common import connect, raw_view
from ingest import digest

class Integridade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=connect(); raw_view(cls.c)
        for view,file in [('e','ocorrencias_elegiveis'),('m','base_modelagem'),('meta','metadados_modelagem'),('s','amostra_experimental_20000'),('q','quarentena_boletins')]:
            cls.c.execute(f"CREATE VIEW {view} AS SELECT * FROM read_parquet('{(ROOT/f'data/processed/{file}.parquet').as_posix()}')")
    def scalar(self,sql): return self.c.execute(sql).fetchone()[0]
    def test_originais_e_intermediarios(self):
        for y in (2023,2024,2025):
            m=json.loads((ROOT/f'data/interim/{y}.json').read_text(encoding='utf-8'))
            self.assertEqual(digest(Path(m['path'])),m['sha256'])
            self.assertEqual(self.scalar(f'SELECT count(*) FROM raw WHERE _source_year={y}'),m['rows'])
            self.assertEqual(self.scalar(f'SELECT count(DISTINCT _source_row) FROM raw WHERE _source_year={y}'),m['rows'])
    def test_recorte_periodo_rotulos(self):
        self.assertGreater(self.scalar('SELECT count(*) FROM e'),0)
        self.assertEqual(self.scalar("SELECT count(*) FROM e WHERE municipio_ibge!='3550308' OR data_fato NOT BETWEEN DATE '2023-01-01' AND DATE '2025-12-31' OR alvo NOT IN (0,1) OR alvo IS NULL"),0)
        self.assertEqual(self.scalar('SELECT count(*)-count(DISTINCT chave_bo) FROM e'),0)
        self.assertEqual(self.scalar('SELECT count(*) FROM e JOIN q USING(chave_bo)'),0)
    def test_rotulo_geografia_e_data_contra_fonte(self):
        # Toda linha de origem de cada BO elegivel deve corroborar o rotulo e o municipio.
        self.assertEqual(self.scalar('''SELECT count(*) FROM raw r JOIN e ON
          sha256(to_json(list_value(upper(trim(NOME_DELEGACIA)),trim(ANO_BO),trim(NUM_BO))))=e.chave_bo
          WHERE upper(trim(NOME_MUNICIPIO_CIRC)) NOT IN ('S.PAULO','SAO PAULO','SÃO PAULO')
          OR (CD_IBGE IS NOT NULL AND upper(trim(CD_IBGE)) NOT IN ('','NULL','3550308'))
          OR upper(trim(RUBRICA))!=CASE e.alvo WHEN 0 THEN 'FURTO (ART. 155)' ELSE 'ROUBO (ART. 157)' END
          OR DATE '1899-12-30'+cast(floor(try_cast(DATA_OCORRENCIA_BO AS DOUBLE)) AS INTEGER)!=e.data_fato'''),0)
        self.assertEqual(self.scalar('SELECT sum(linhas_vinculadas) FROM e'),self.scalar('''SELECT count(*) FROM raw r JOIN e ON
          sha256(to_json(list_value(upper(trim(NOME_DELEGACIA)),trim(ANO_BO),trim(NUM_BO))))=e.chave_bo'''))
    def test_esquema_sem_identificadores(self):
        allowed=['mes','dia_semana','periodo_fato','tipo_local','bairro','alvo']
        schema=[r[0] for r in self.c.execute('DESCRIBE m').fetchall()]
        self.assertEqual(schema,allowed)
        self.assertEqual(self.scalar("SELECT count(*) FROM m WHERE mes NOT BETWEEN 1 AND 12 OR dia_semana NOT BETWEEN 0 AND 6 OR periodo_fato NOT IN ('MADRUGADA','MANHA','TARDE','NOITE','INCERTO')"),0)
        self.assertEqual(self.scalar('SELECT count(*) FROM m'),self.scalar('SELECT count(*) FROM e'))
    def test_alinhamento_metadados(self):
        self.assertEqual(self.scalar('SELECT count(*) FROM meta'),self.scalar('SELECT count(*) FROM m'))
        self.assertEqual(self.scalar('SELECT count(*)-count(DISTINCT indice_linha) FROM meta'),0)
        self.assertEqual(self.scalar('''SELECT count(*) FROM
          (SELECT row_number() OVER()-1 i,* FROM m) m JOIN meta ON i=indice_linha JOIN e USING(chave_bo)
          WHERE m.alvo!=e.alvo OR m.mes!=e.mes OR m.dia_semana!=e.dia_semana
          OR m.periodo_fato IS DISTINCT FROM e.periodo_fato
          OR m.tipo_local IS DISTINCT FROM e.tipo_local OR m.bairro IS DISTINCT FROM e.bairro'''),0)
    def test_harmonizacao_periodo(self):
        self.assertEqual(self.scalar('''SELECT count(*) FROM e WHERE periodo_fato IS DISTINCT FROM
          CASE WHEN hora BETWEEN 0 AND 5 THEN 'MADRUGADA' WHEN hora BETWEEN 6 AND 11 THEN 'MANHA'
          WHEN hora BETWEEN 12 AND 17 THEN 'TARDE' WHEN hora BETWEEN 18 AND 23 THEN 'NOITE'
          WHEN periodo='DE MADRUGADA' THEN 'MADRUGADA' WHEN periodo='PELA MANHÃ' THEN 'MANHA'
          WHEN periodo='A TARDE' THEN 'TARDE' WHEN periodo='A NOITE' THEN 'NOITE'
          WHEN periodo='EM HORA INCERTA' THEN 'INCERTO' END'''),0)
    def test_amostra_proporcional_e_subconjunto(self):
        n=self.scalar('SELECT count(*) FROM e')
        self.assertEqual(self.scalar('SELECT count(*) FROM s'),min(20000,n))
        self.assertEqual(self.scalar('SELECT count(*)-count(DISTINCT chave_bo) FROM s'),0)
        self.assertEqual(self.scalar('SELECT count(*) FROM (SELECT * FROM s EXCEPT SELECT * FROM e)'),0)
        self.assertEqual(self.scalar('''SELECT count(*) FROM
         (SELECT ano_fato,mes,alvo,count(*) n FROM s GROUP BY 1,2,3) a JOIN
         (SELECT ano_fato,mes,alvo,count(*) n FROM e GROUP BY 1,2,3) b USING(ano_fato,mes,alvo)
         WHERE abs(a.n-b.n*20000.0/(SELECT count(*) FROM e))>=1'''),0)
    def test_reconciliacao_unidades(self):
        n=self.scalar('SELECT count(DISTINCT (NOME_DELEGACIA,ANO_BO,NUM_BO)) FROM raw')
        self.assertEqual(n,self.scalar('SELECT count(*) FROM e')+self.scalar('SELECT count(*) FROM q'))

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Integridade)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    out={'executados':result.testsRun,'falhas':len(result.failures),'erros':len(result.errors),'sucesso':result.wasSuccessful()}
    (ROOT/'reports/testes_integridade.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    sys.exit(0 if result.wasSuccessful() else 1)
