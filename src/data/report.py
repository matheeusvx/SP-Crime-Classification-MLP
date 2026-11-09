"""Relatorio, figuras e notebook executado a partir de agregados locais."""
import base64
import contextlib
import io
from common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def read(name):
    with (ROOT/f'reports/tables/{name}.csv').open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def md(rows,cols=None):
    if not rows: return '(sem registros)'
    cols=cols or list(rows[0])
    return '| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+'\n'.join('| '+' | '.join(str(r.get(c,'' )).replace('|','/') for c in cols)+' |' for r in rows)

RECOMMENDATIONS={
 'mes':('DATA_OCORRENCIA_BO','Mês do fato','Transformar ciclicamente ou One-Hot; não usar mês estatístico/registro.','baixo','transformar'),
 'dia_semana':('DATA_OCORRENCIA_BO','Dia da semana, segunda=0','One-Hot ou seno/cosseno; código não representa intensidade.','baixo','transformar'),
 'periodo_fato':('HORA_OCORRENCIA + DESCR_PERIODO','Faixa temporal unificada do fato','One-Hot nominal. Convenção operacional: 00–05 madrugada, 06–11 manhã, 12–17 tarde, 18–23 noite; usa período declarado quando não há hora. Hora incerta vira INCERTO.','não revela a natureza; investigar incerteza e convenção de faixas','transformar'),
 'tipo_local':('DESCR_TIPOLOCAL','Grupo de local do fato','One-Hot; local informado pode diferenciar contextos, sem revelar diretamente natureza.','baixo','utilizar'),
 'bairro':('BAIRRO','Bairro informado no boletim','2.328 categorias; grafias livres. Agrupar raras só no treino, com handle_unknown; não equiparar automaticamente a distrito oficial.','baixo direto; risco de memorização','investigar')}

def report():
    con=connect()
    con.execute(f"CREATE VIEW e AS SELECT * FROM read_parquet('{(ROOT/'data/processed/ocorrencias_elegiveis.parquet').as_posix()}')")
    save_table(con,'''SELECT ano_fato,alvo,count(*) boletins,
       count(*) FILTER(WHERE hora IS NULL) hora_ausente,count(*) FILTER(WHERE periodo IS NULL) periodo_ausente,
       count(*) FILTER(WHERE hora IS NULL AND periodo IS NULL) ambos_ausentes,
       count(*) FILTER(WHERE hora IS NOT NULL AND periodo IS NOT NULL) ambos_presentes,
       count(*) FILTER(WHERE hora=0) hora_zero FROM e GROUP BY 1,2 ORDER BY 1,2''','qualidade_temporal_atributos')
    inventory=json.loads((ROOT/'reports/inventario.json').read_text(encoding='utf-8'))
    profiles=read('perfil_colunas'); attrs=json.loads((ROOT/'reports/perfil_atributos.json').read_text(encoding='utf-8'))
    n=con.execute('SELECT count(*) FROM e').fetchone()[0]
    nr=sum(x['rows'] for x in inventory); gran=read('granularidade')[0]
    bo=int(gran['boletins']); decisions=read('decisoes_boletins'); eligible_lines=next(int(x['linhas_origem']) for x in decisions if x['decisao']=='elegivel')
    recommendations=[]
    for a in attrs:
        orig,meaning,transform,risk,decision=RECOMMENDATIONS[a['atributo']]
        recommendations.append({'original':orig,'padronizada':a['atributo'],'significado':meaning,
          'tipo':'inteiro derivado' if a['atributo'] in ['mes','dia_semana','hora'] else 'categoria nominal',
          'ausentes_pct':a['ausentes_pct'],'cardinalidade':a['cardinalidade'],'qualidade_e_transformacao':transform,
          'relacao_com_tarefa':'contexto temporal/espacial da ocorrência; utilidade preditiva ainda não medida',
          'risco_leakage':risk,'recomendacao':decision})
    with (ROOT/'reports/tables/recomendacao_atributos.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(recommendations[0])); w.writeheader(); w.writerows(recommendations)
    # Dicionario original e avaliacao de todos os atributos, nao apenas candidatos.
    support=json.loads((ROOT/'reports/documentacao_fonte.json').read_text(encoding='utf-8'))
    dictionary=[]
    forbidden={'RUBRICA','DESC_LEI','DESCR_CONDUTA','DESDOBRAMENTO','CIRCUNSTANCIA','FLAG_STATUS','FLAG_ATO_INFRACIONAL'}
    sensitive={'LOGRADOURO','NUMERO_LOGRADOURO','LATITUDE','LONGITUDE','CEP'}
    candidates={'BAIRRO','HORA_OCORRENCIA','DESCR_PERIODO','DESCR_TIPOLOCAL','DATA_OCORRENCIA_BO'}
    identifiers={'ID_DELEGACIA','NOME_DELEGACIA','NUM_BO','ANO_BO','VERSAO','LOGRADOURO_VERSAO','CONT_OBJETO'}
    for x in support:
        desc={v[0]:v[1] for _,v in x['support']['dictionary'] if len(v)>1 and v[0] and v[1]}
        desc['CD_IBGE']=desc.get('COD IBGE','Não descrito')+'; geografia de referência não explicitada'
        for col in x['headers']:
            p=next(v for v in profiles if v['original']==col and int(v['ano_arquivo'])==x['year'])
            reason=('alvo/derivado jurídico: vazamento direto ou suspeito' if col in forbidden else
                    'endereço ou localização precisa: excluir por privacidade' if col in sensitive else
                    'chave administrativa/item: somente rastreabilidade' if col in identifiers else
                    'candidato contextual; ver recomendacao_atributos.csv' if col in candidates else
                    'não selecionado: administrativo, pós-registro, objeto ou contexto sem necessidade demonstrada')
            dictionary.append(p|{'significado_fonte':desc.get(col,'Não descrito'),'avaliacao':reason})
    with (ROOT/'reports/tables/dicionario_dados.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(dictionary[0]));w.writeheader();w.writerows(dictionary)
    schema=[]
    for col in sorted(set(p['original'] for p in profiles)):
        schema.append({'coluna':col,**{str(y):'presente' if any(p['original']==col and int(p['ano_arquivo'])==y for p in profiles) else 'ausente' for y in (2023,2024,2025)}})
    with (ROOT/'reports/tables/comparacao_esquemas.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(schema[0]));w.writeheader();w.writerows(schema)
    figure(attrs)
    totalclasses=read('classes_total'); byyear=read('classes_por_ano'); geo=read('recorte_linhas')
    origtable=[{'arquivo':Path(x['path']).name,'ano':x['year'],'MB_decimais':round(x['bytes']/1e6,2),'abas':len(x['sheets']),'colunas':len(x['columns']),'linhas':x['rows'],'leitura_s':x['seconds'],'RSS_amostrado_MB':x['rss_peak_sampled_mb']} for x in inventory]
    levels=sum(a['cardinalidade']+1 for a in attrs)
    dense=lambda size:round(size*levels*4/1024**2,1)
    sizes=[{'arquivo':p.name,'MB_decimais':round(p.stat().st_size/1e6,3)} for p in sorted((ROOT/'data/processed').glob('*.parquet'))]
    tests=json.loads((ROOT/'reports/testes_integridade.json').read_text(encoding='utf-8'))
    reporttext=f'''# Etapa 1 — Segurança Pública Inteligente em São Paulo

Execução local em 09/11/2026. Somente preparação, sem treinamento ou aplicação web.

## A. Arquivos analisados

{md(origtable)}

Todos são XLSX OOXML reais, com metodologia, dicionário e uma aba de dados. São 55 colunas por arquivo; esquema detalhado e diferenças em `tables/comparacao_esquemas.csv`. Originais preservados e verificados por SHA256. O universo é de boletins com celulares subtraídos, não de todos os crimes da capital. Proveniência e referências em `../docs/decisoes.md`.

## B. Recorte e tratamento

{md(geo)}

Filtro primário: `NOME_MUNICIPIO_CIRC`, município da circunscrição do fato; `CD_IBGE=3550308` corrobora quando preenchido. Não usar `NOME_MUNICIPIO` do registro. Não houve município ausente nem conflito IBGE/capital nas linhas; existem BOs com linhas de diferentes municípios. `CIDADE` tem descrição divergente entre dicionários e não é usada para filtrar. Não há geocodificação independente de cada endereço; a validação é semântica e por consistência dos campos da fonte.

As {nr:,} linhas representam {bo:,} chaves distintas de boletim. O resultado é **{n:,} boletins elegíveis**, sustentados por {eligible_lines:,} linhas originais. Há {bo-n:,} boletins segregados ({100*(bo-n)/bo:.2f}% das chaves). {nr-eligible_lines:,} linhas não pertencem a BOs elegíveis ({100*(nr-eligible_lines)/nr:.2f}% das linhas); outras {eligible_lines-n:,} são vínculos consolidados dos BOs mantidos, não exclusões de crimes. Não confundir esses denominadores.

{md(decisions)}

Os motivos são mutuamente exclusivos por prioridade: geografia, data inválida/conflitante, período, duas classes, ausência de classe e outras naturezas. Os critérios secundários e sobreposições são diagnosticados nas demais tabelas. BOs com múltiplas naturezas são segregados conservadoramente; isso reduz cobertura e pode selecionar casos mais simples. Essa decisão deve ser avaliada antes de ampliar o escopo.

## C. Classes

Convenção: **0=FURTO; 1=ROUBO**. Só igualdade normalizada com `Furto (art. 155)` ou `Roubo (art. 157)`. Nenhuma regra por substring. “Furto de coisa comum (art. 156)” não é equiparado automaticamente. Todas as demais rubricas e suas frequências/decisões estão em `tables/mapeamento_classes.csv`. Qualificadoras são mantidas dentro da rubrica reconhecida; não são atributos. Todos os registros observados têm `FLAG_STATUS=CONSUMADO`; não há tentativas para avaliar nesta entrega.

{md(totalclasses)}

{md(byyear)}

O ano acima é o do fato, não o do arquivo nem do registro. Há desbalanceamento moderado e mudança da proporção de classes entre anos; não houve balanceamento artificial. Comparações temporais descrevem esta extração e seus filtros, não as estatísticas oficiais de criminalidade.

## D. Qualidade

{md(read('datas_data_ocorrencia_bo'))}

As datas mínimas chegam a 2003, apesar dos nomes dos arquivos 2023–2025. Datas fora do ano do arquivo são sinalizadas; fatos de outro ano ainda em 2023–2025 podem permanecer. Fatos anteriores a 2023 são segregados. Datas de registro anteriores ao fato são inconsistências da fonte, contadas abaixo. A elegibilidade usa a data do fato válida; esses atrasos negativos não são corrigidos nem usados como atributos. Não há evidência externa para reconstruir a data correta.

{md(read('atraso_registro'))}

{md([gran])}

{md(read('duplicatas_exatas'))}

Não foram encontradas linhas integralmente idênticas por arquivo, mas há muitos vínculos por boletim. A inspeção conjunta encontra quatro chaves em múltiplos arquivos. Repetições são consolidadas por chave, não removidas sem examinar natureza, data e geografia. Não é possível detectar com segurança dois BOs diferentes que descrevam o mesmo fato; falta um identificador universal do evento.

`NULL`, vazio, `N/A` e `NAN` são marcadores explícitos de ausência. Códigos e identificadores permanecem textuais no intermediário. Valores categóricos recebem apenas trim e maiúsculas; não há fusão automática de bairros por semelhança. Em boletins elegíveis, 184 conflitos de tipo de local e 470 de bairro viram ausente; a regra usa consenso dos valores não ausentes e não escolhe a primeira linha. `FLAG_STATUS` é constante, portanto não acrescenta informação.

`tables/perfil_colunas.csv` registra por campo/ano quantos marcadores de ausência são convertidos em nulo e quantas linhas seriam alteradas por trim ou maiúsculas. Maiúsculas são aplicadas somente nas comparações de chaves/rubricas/município e na consolidação de categorias, não indiscriminadamente em todo o intermediário. `ambiente.json` documenta Python, versões das dependências e recursos disponíveis.

## E. Atributos candidatos

{md(attrs)}

Recomendações completas, significado, tipos, transformações e riscos em `tables/recomendacao_atributos.csv`; os 165 perfis de coluna/ano e seus significados estão em `tables/dicionario_dados.csv`.

Hora e período brutos têm 48,47% e 51,53% de ausência, respectivamente, com ausência complementar e fortemente associada à classe. Por isso **não são entradas separadas**, nem se fornece um indicador de qual campo veio preenchido. `periodo_fato` harmoniza hora conhecida e período declarado: 00–05=MADRUGADA, 06–11=MANHA, 12–17=TARDE, 18–23=NOITE; “Em hora incerta”=INCERTO. As faixas são uma convenção operacional deste projeto, não uma definição confirmada da SSP; não se inventa uma hora exata para períodos amplos. A incerteza temporal ainda pode refletir o processo de registro e deve ser investigada. `tables/qualidade_temporal_atributos.csv` preserva a evidência por ano/classe. Bairro tem cardinalidade elevada e grafias livres, não deve ser confundido com distrito administrativo. Sua inclusão definitiva e a sensibilidade às faixas de período ficam para avaliação na Etapa 2, sem usar desempenho do teste final.

Campos de natureza, lei, conduta, desdobramento, circunstância e sinalizadores jurídicos ficam fora das entradas. Identificadores, coordenadas precisas, logradouro, número, CEP, campos pós-registro, marca de objeto, corporação apresentante e autoria também não são selecionados. Ano do fato, chave e data completa ficam apenas nos metadados. A base de modelagem recebe cinco atributos contextuais e a coluna-alvo separável; nenhum codificador foi ajustado.

## Análise exploratória

![Distribuições e qualidade](figures/painel_exploratorio.png)

As tabelas de classes mensais cobrem ano/mês do fato; distribuições de bairro e período preservam ausentes. Gráficos são descritivos e não evidenciam causalidade nem risco futuro. Não há medição de utilidade preditiva nesta etapa.

## F. Arquivos produzidos

{md(sizes)}

- `data/interim/2023.parquet`, `2024.parquet`, `2025.parquet`: cópias intermediárias locais, com lexemas originais e rastreabilidade.
- `data/processed/ocorrencias_elegiveis.parquet`: uma linha por BO, atributos, classe e metadados analíticos, sem endereço preciso.
- `data/processed/base_modelagem.parquet`: apenas cinco candidatos e alvo; `esquema_modelagem.json` define a lista explícita de entradas.
- `data/processed/metadados_modelagem.parquet`: chave, data, ano e município, alinhados por índice de linha à base de modelagem.
- `data/processed/quarentena_boletins.parquet`: chave e motivo de segregação; os originais permitem investigar os vínculos, sem exemplos pessoais no relatório.
- `data/processed/amostra_experimental_20000.parquet`: amostra de BOs elegíveis com metadados; selecionar as mesmas cinco entradas para modelar.
- `src/data/`: scripts reutilizáveis; `notebooks/01_auditoria_exploracao.ipynb`: análise executada com agregados.
- `reports/tables/`: auditoria, mapeamento, distribuições, perdas e amostragem; `tests/test_integridade.py`: testes independentes.

Verificação automatizada: **{tests['executados']} testes executados; {tests['falhas']} falhas; {tests['erros']} erros**. Inclui conservação por SHA256, recorte/período/rótulos contra todas as linhas da fonte, unicidade, esquema permitido, reconciliação de unidades, alinhamento e cotas amostrais. Os testes falham com saída diferente de zero, sem ocultar problemas.

## G. Cenários e recomendações para a Etapa 2

**A — 20 mil BOs:** cotas proporcionais por ano, mês e classe, pelo método de maior resto e ordenação SHA256 com semente textual fixa. Reproduzível e sem equilíbrio forçado; pode perder categorias raras. A amostra é subconjunto do cenário B e não constitui avaliação independente.

**B — {n:,} BOs:** maior cobertura de períodos e categorias, maior custo de treino e memória. Não há garantia de maior acurácia. Não contar múltiplos vínculos como exemplos adicionais.

Estimativa ilustrativa de matriz One-Hot densa float32, incluindo uma categoria ausente por variável e todos os níveis observados: {levels:,} colunas, cerca de **{dense(20000):,.1f} MiB** para A e **{dense(n):,.1f} MiB** para B, apenas entradas, sem pesos, ativações ou otimizador. É uma estimativa de teto descritivo, não um codificador ajustado. Sparse e lotes reduzem o armazenamento; uma futura MLP pode exigir densificação por lote. Agrupar bairros raros exclusivamente no treino pode reduzir a dimensão.

Proposta a revisar: treino com fatos de 2023, validação 2024, teste final 2025. A chave de BO deve permanecer indivisa. Não foi fixada nem materializada uma divisão nesta etapa. Ajustar One-Hot, imputação, categorias raras e escalas apenas no treino, com tratamento de valores desconhecidos. Considerar codificação cíclica para tempo e classe majoritária como referência na avaliação posterior. Não usar teste para escolher atributos, arquitetura ou hiperparâmetros.

## H. Pendências para avaliação do usuário

1. Aceitar a exclusão conservadora dos BOs com outras naturezas associadas ou solicitar estudo de ampliação, sem atribuir um único crime a um objeto por suposição.
2. Revisar a convenção do período harmonizado e a inclusão de bairros de alta cardinalidade, com tratamento aprendido somente no treino.
3. Confirmar a proposta temporal e o cenário experimental/ampliado, considerando o domínio restrito a celulares e a mudança de sistemas da SSP.
4. A semântica geográfica exata de `CD_IBGE` não está explicitada no dicionário; foi usado como corroborador. `CIDADE` tem documentação contraditória e foi excluída do critério. Não há validação externa de endereços nem reconstrução de datas inconsistentes.

As pendências delimitam escolhas da próxima etapa e limitações da fonte. Não impedem reproduzir a base conservadora entregue. **A execução para nesta Etapa 1.**
'''
    (ROOT/'reports/relatorio_etapa1.md').write_text(reporttext,encoding='utf-8')
    notebook(reporttext)
    print(reporttext)

def figure(attrs):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,3,figsize=(19,11),layout='constrained')
    colors=['#126C8A','#EF9A42']; names=['Furto','Roubo']
    year=read('classes_por_ano'); years=['2023','2024','2025']
    for k in range(2):
        vals=[next(int(r['boletins']) for r in year if r['ano_fato']==y and r['alvo']==str(k)) for y in years]
        axes[0,0].bar([i+(k-.5)*.36 for i in range(3)],vals,.36,label=names[k],color=colors[k])
    axes[0,0].set_xticks(range(3),years); axes[0,0].set_title('Boletins elegíveis por ano do fato');axes[0,0].legend();axes[0,0].set_ylabel('Boletins')
    months=read('classes_mensal'); m=sorted(set(r['mes_fato'] for r in months))
    for k in range(2):
        vals=[next((int(r['boletins']) for r in months if r['mes_fato']==x and r['alvo']==str(k)),0) for x in m]
        axes[0,1].plot(range(len(m)),vals,color=colors[k],label=names[k],lw=2)
    axes[0,1].set_xticks(range(0,len(m),6),[m[i] for i in range(0,len(m),6)],rotation=30);axes[0,1].set_title('Evolução mensal — fatos');axes[0,1].legend();axes[0,1].set_ylabel('Boletins')
    cl=read('classes_total'); axes[0,2].bar(names,[float(x['percentual']) for x in cl],color=colors)
    for k,r in enumerate(cl): axes[0,2].text(k,float(r['percentual'])+1,f"{float(r['percentual']):.1f}%",ha='center')
    axes[0,2].set_ylim(0,75);axes[0,2].set_title('Classes após consolidação');axes[0,2].set_ylabel('% dos boletins elegíveis')
    axes[1,0].barh([a['atributo'] for a in attrs],[a['ausentes_pct'] for a in attrs],color='#126C8A');axes[1,0].set_xlim(0,65);axes[1,0].set_title('Ausência dos candidatos');axes[1,0].set_xlabel('% dos boletins elegíveis')
    for i,a in enumerate(attrs): axes[1,0].text(a['ausentes_pct']+1,i,f"{a['ausentes_pct']:.1f}%",va='center')
    for ax,table,col,title in [(axes[1,1],'distribuicao_periodo_fato','periodo_fato','Período harmonizado do fato'),(axes[1,2],'distribuicao_bairro','bairro','10 bairros mais frequentes')]:
        rows=read(table); counts={}
        for r in rows: counts[r[col] or '(AUSENTE)']=counts.get(r[col] or '(AUSENTE)',0)+int(r['boletins'])
        top=sorted(counts.items(),key=lambda x:x[1],reverse=True)[:10]
        ax.barh([x[0] for x in top][::-1],[x[1] for x in top][::-1],color='#126C8A');ax.set_title(title);ax.set_xlabel('Boletins elegíveis')
    fig.suptitle('SSP-SP • Celulares subtraídos • São Paulo capital\nUma observação por boletim | 2023–2025 pelo fato | análise descritiva',fontsize=17,fontweight='bold')
    (ROOT/'reports/figures').mkdir(exist_ok=True)
    fig.savefig(ROOT/'reports/figures/painel_exploratorio.png',dpi=150);plt.close(fig)

def notebook(reporttext):
    cells=[]
    def mark(s): cells.append({'cell_type':'markdown','metadata':{},'source':s.splitlines(keepends=True)})
    def code(s): cells.append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':s.splitlines(keepends=True)})
    mark('# Etapa 1 — Auditoria e exploração\n\nFIAP Global Solution 2026.2. Classificação de ocorrências com MLP. Esta etapa não treina modelos nem prevê crimes futuros. Fontes: os três XLSX CelularesSubtraidos_2023/2024/2025, fornecidos em D:/, com metodologia e dicionário próprios. Os originais não são carregados neste notebook. Proveniência completa em `../docs/decisoes.md`.')
    code("from pathlib import Path\nimport csv, json\nROOT = Path.cwd()\nif not (ROOT / 'reports').exists(): ROOT = ROOT.parent\nassert (ROOT / 'reports/inventario.json').exists(), 'Execute o pipeline antes do notebook'\ndef tabela(nome):\n    with (ROOT / f'reports/tables/{nome}.csv').open(encoding='utf-8-sig', newline='') as f:\n        rows=list(csv.reader(f))\n    for row in rows: print(' | '.join(row))\n")
    mark('## Estrutura e proveniência\n\n55 colunas por ano; 3 abas por XLSX. Em 2025, os campos de mês/ano passam a ser explicitamente do registro. Não os interpretar como data do fato. As tabelas completas de esquema e dicionário ficam em reports/tables.')
    code("inventory=json.loads((ROOT/'reports/inventario.json').read_text(encoding='utf-8'))\nfor f in inventory:\n    print(Path(f['path']).name, 'linhas:', f['rows'], 'colunas:',len(f['columns']), 'SHA256:',f['sha256'])\n")
    mark('## Geografia e granularidade\n\nFiltro pelo município de circunscrição, com código IBGE corroborativo. Município de registro não define o local do fato. Cada linha original representa um vínculo; a unidade consolidada é a tupla de delegacia, ano e número do BO. Naturezas, datas ou geografia incompatíveis levam à segregação, com rastreabilidade local.')
    code("tabela('recorte_linhas')\ntabela('granularidade')\ntabela('decisoes_boletins')\n")
    mark('## Classes e período\n\n0=FURTO (rubrica exata art. 155), 1=ROUBO (rubrica exata art. 157). Outras naturezas e classes conflitantes não são rotuladas por substring. O ano deriva da data do fato. A base não constitui a estatística oficial da SSP.')
    code("tabela('classes_total')\ntabela('classes_por_ano')\ntabela('datas_data_ocorrencia_bo')\n")
    mark('## Exploração e qualidade\n\nHá desbalanceamento moderado, mudança da proporção entre anos e ausências elevadas de hora/período. Bairro tem alta cardinalidade e grafias livres. Essas constatações orientam inspeção e engenharia; utilidade preditiva não foi medida. As tabelas de qualidade temporal permitem inspecionar a ausência complementar, sem imputar horas arbitrárias.')
    code("attrs=json.loads((ROOT/'reports/perfil_atributos.json').read_text(encoding='utf-8'))\nfor a in attrs: print(a)\ntabela('qualidade_temporal_atributos')\n")
    mark('![Painel exploratório](../reports/figures/painel_exploratorio.png)')
    mark('## Preparação e integridade\n\nA base de modelagem tem apenas cinco candidatos contextuais e alvo. Hora e período brutos foram excluídos como entradas separadas, porque o padrão de preenchimento varia fortemente entre classes. O período harmonizado usa a convenção 00–05 madrugada, 06–11 manhã, 12–17 tarde e 18–23 noite, ou o período declarado na ausência de hora; “Em hora incerta” é INCERTO. As faixas são uma decisão operacional, não uma definição confirmada da SSP. Não existe indicador de qual campo veio preenchido. Chaves, data completa e município estão em metadados alinhados por índice. Não há natureza como entrada, endereço, coordenada precisa ou identificadores administrativos. Nenhum imputador, codificador ou escalonador foi ajustado. Os testes confrontam os resultados com as linhas originais e conferem os hashes.')
    code("print((ROOT/'reports/testes_integridade.json').read_text(encoding='utf-8'))\nprint((ROOT/'data/processed/esquema_modelagem.json').read_text(encoding='utf-8'))\n")
    mark('## Cenários e próximos passos\n\nA amostra de 20 mil BOs preserva proporções por ano/mês/classe com cotas de maior resto e semente determinística. A base ampliada melhora cobertura, com maior custo e sem promessa de maior acurácia. Proposta ainda não fixada: 2023 treino, 2024 validação, 2025 teste. Ajustar transformadores e categorias raras somente no treino; manter BOs indivisos.\n\nRevisar com o usuário: exclusão de outras naturezas associadas, bairros de alta cardinalidade, representação conjunta hora/período e a divisão temporal. Ver o relatório completo em `../reports/relatorio_etapa1.md`. O trabalho termina nesta etapa.')
    namespace={'__name__':'__main__'}; count=0
    for c in cells:
        if c['cell_type']!='code':continue
        count+=1; buf=io.StringIO()
        with contextlib.redirect_stdout(buf):exec(''.join(c['source']),namespace)
        c['execution_count']=count
        c['outputs']=[{'output_type':'stream','name':'stdout','text':buf.getvalue().splitlines(keepends=True)}]
    nb={'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':sys.version.split()[0]}},'nbformat':4,'nbformat_minor':5}
    import uuid
    for c in cells:c['id']=uuid.uuid5(uuid.NAMESPACE_URL,''.join(c['source'])).hex[:12]
    (ROOT/'notebooks').mkdir(exist_ok=True)
    (ROOT/'notebooks/01_auditoria_exploracao.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1),encoding='utf-8')

if __name__=='__main__':report()
