"""Relatorio da Etapa 2 e notebook executado, sem predicoes para 2025."""
from ml.runtime import *
import csv
import json
import io
import contextlib
import uuid
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ml.dataset import connection,load_year
from ml.inference import ClassificadorOcorrencias

def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
def table(rows,cols=None):
    if not rows:return '(sem linhas)'
    cols=cols or list(rows[0]);fmt=lambda v:f'{v:.4f}' if isinstance(v,float) else str(v)
    return '| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+'\n'.join('| '+' | '.join(fmt(r.get(c,'')) for c in cols)+' |' for r in rows)
def csv_write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def figures(history,metrics):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained');xs=[h['epoca'] for h in history]
    for ax,k,title in [(axes[0],'loss','Binary Cross-Entropy'),(axes[1],'accuracy','Acurácia')]:
        ax.plot(xs,[h[k] for h in history],label='Treino · 2023',color='#126C8A')
        ax.plot(xs,[h['val_'+k] for h in history],label='Validação · 2024',color='#DB7E22')
        best=1+int(np.argmin([h['val_loss'] for h in history]));ax.axvline(best,ls='--',color='#777777',label=f'Melhor época: {best}')
        ax.set_xlabel('Época');ax.set_title(title);ax.legend()
    fig.suptitle('MLP inicial · 64 ReLU → 1 sigmoid · 2025 sem avaliação',fontweight='bold')
    fig.savefig(ROOT/'reports/figures/curvas_mlp_baseline.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,5),layout='constrained')
    for ax,m in zip(axes,[next(m for m in metrics if m['modelo']=='Majoritario'),next(m for m in metrics if m['modelo']=='MLP' and m['ano']==2024)]):
        cm=np.asarray(m['matriz_confusao']);ax.imshow(cm,cmap='Blues',vmin=0,vmax=158895)
        for i in range(2):
            for j in range(2):ax.text(j,i,f'{cm[i,j]:,}'.replace(',','.'),ha='center',va='center',fontsize=16)
        ax.set_xticks([0,1],['FURTO','ROUBO']);ax.set_yticks([0,1],['FURTO','ROUBO'])
        ax.set_xlabel('Classe prevista');ax.set_ylabel('Classe verdadeira');ax.set_title(m['modelo'])
    fig.suptitle('Validação 2024 · Matriz de confusão · Mesmo conjunto para as duas referências',fontweight='bold')
    fig.savefig(ROOT/'reports/figures/matriz_confusao_baseline.png',dpi=150);plt.close(fig)

def report():
    config=json.loads((MODELS/'config_modelo.json').read_text(encoding='utf-8'))
    metrics=read('metricas_baseline.json');history=read('historico_mlp.json');pre=read('preprocessamento.json')
    data=read('validacao_dados.json');tests=read('testes_etapa2.json')
    columns=['modelo','ano','n','accuracy','precision','recall','f1','macro_f1','balanced_accuracy']
    rows=[{k:m[k] for k in columns} for m in metrics]
    csv_write(ROOT/'reports/tables/metricas_baseline.csv',rows)
    classrows=[{'modelo':m['modelo'],'ano':m['ano'],'classe':cl,**vals} for m in metrics for cl,vals in m['por_classe'].items()]
    csv_write(ROOT/'reports/tables/metricas_baseline_por_classe.csv',classrows)
    figures(history,metrics)
    # Diagnostico por grupo somente na validacao, apos congelar modelo e limiar.
    c=connection();records,y,_=load_year(c,2024);predictions=np.load(OUT/'validacao_predicoes.npz');prob=predictions['prob_roubo'];pred=(prob>=.5).astype(int)
    import collections
    grouprows=[]
    for feature in ['tipo_local','mes','dia_semana','bairro']:
        groups=collections.defaultdict(list)
        for i,r in enumerate(records):groups[r[feature] if r[feature] is not None else '(AUSENTE)'].append(i)
        for value,ids in groups.items():
            ids=np.asarray(ids)
            if len(ids)<50:continue
            errors=int(np.sum(y[ids]!=pred[ids]))
            grouprows.append({'atributo':feature,'categoria':value,'boletins':len(ids),'erros':errors,
               'taxa_erro':errors/len(ids),'furtos_verdadeiros':int(sum(y[ids]==0)),'roubos_verdadeiros':int(sum(y[ids]==1))})
    grouprows.sort(key=lambda r:r['erros'],reverse=True);csv_write(OUT/'erros_por_grupo_validacao.csv',grouprows)
    top=[r for r in grouprows if r['atributo']=='tipo_local'][:8]
    classifier=ClassificadorOcorrencias();example=classifier.classificar(5,2,'VIA PÚBLICA','BELA VISTA')
    json_write(OUT/'exemplo_inferencia.json',{'entrada':{'mes':5,'dia_semana':2,'tipo_local':'VIA PÚBLICA','bairro':'BELA VISTA'},'saida':example})
    train=next(m for m in metrics if m['modelo']=='MLP' and m['ano']==2023)
    val=next(m for m in metrics if m['modelo']=='MLP' and m['ano']==2024)
    baseline=next(m for m in metrics if m['modelo']=='Majoritario')
    best=config['best_epoch'];peak=max(h['rss_mb'] for h in history)
    diff=100*(val['accuracy']-baseline['accuracy']);f1diff=val['macro_f1']-baseline['macro_f1']
    dense_mib=config['input_dimension']*config['train_rows']*4/1024**2
    ntests=sum(t['executados'] for t in tests)
    fail=read('consistencia_recarga.json')
    prep=[{'conjunto':label,'n':p['rows'],'bairro_ausente':p['bairro']['ausentes_entrada'],'bairro_raro_bucket':p['bairro']['raros'],
      'bairro_novo':p['bairro']['desconhecidos'],'tipo_local_ausente':p['tipo_local']['ausentes_entrada'],'tipo_local_novo':p['tipo_local']['desconhecidos']} for label,p in pre.items()]
    text=f'''# Etapa 2 — Primeira MLP para celulares subtraídos

Execução em 09/11/2026. Uma única arquitetura, treinada efetivamente. Não há aplicação web nem comparação sistemática de arquiteturas. O domínio é o extrato SSP-SP de **boletins envolvendo celulares subtraídos em São Paulo capital**, tratado na Etapa 1. Não representa todos os crimes da cidade nem previsão de risco criminal futuro.

## A. Dados utilizados e integridade

Treinamento: **{config['train_rows']:,} boletins de 2023**. Validação: **{config['validation_rows']:,} de 2024**. Teste final: **{config['test_rows_isolated']:,} de 2025, sem transformação preditiva, previsões ou métricas**. Toda a base permitida foi utilizada; a amostra de 20 mil não foi necessária. O ano foi derivado da data do fato nos metadados.

Antes de treinar, foram conferidos esquema, tipos, rótulos, índices contíguos, chaves únicas e ausência de sobreposição temporal. O alinhamento foi verificado célula a célula contra `ocorrencias_elegiveis.parquet`, por chave e índice, incluindo rótulo e data. Não se confiou apenas na posição das linhas. Uma perturbação em memória nos metadados é rejeitada pelos testes.

{table(data['duplicidade_contextos'])}

Tuplas de atributos iguais em BOs diferentes são esperadas e **não foram removidas**. Existem contextos idênticos associados às duas classes, evidenciando que as quatro entradas não determinam a resposta. A base consolidada permanece com uma observação por boletim e com as exclusões conservadoras da Etapa 1.

Hashes dos artefatos anteriores constam em `etapa2/etapa1_preservacao.json` e são reconferidos nos testes. Os arquivos da Etapa 1, seus relatórios, notebook e oito testes foram preservados. As únicas leituras de 2025 nesta etapa são verificações estruturais de alinhamento, contagem e chaves, sem escolher vocabularios, frequências, hiperparâmetros ou atributos a partir dele.

## B. Pré-processamento e inspeção semântica

Entradas exatas: **`mes`, `dia_semana`, `tipo_local`, `bairro`**. O alvo é separado: **0=FURTO, 1=ROUBO**. `periodo_fato`, hora, indicadores de preenchimento temporal, ano, chave, data completa, natureza, rubricas, lei, endereço e coordenadas não entram no pré-processador nem no modelo.

Mês e dia da semana recebem One-Hot, sem impor magnitude ou distância ordinal. Todas as quatro variáveis são categóricas. Os intervalos válidos são mês 1–12 e dia 0–6, segunda-feira=0. Valores numéricos inválidos e colunas extras são rejeitados. Ausências recebem categoria explícita, sem remover linhas. Não há escalonamento, imputação por moda ou balanceamento artificial.

Tipos de local e bairros foram inspecionados **somente no treino**. Foram examinadas frequências, categorias raras e possíveis equivalências; a varredura de termos de natureza criminal não encontrou rubricas, roubo ou furto nas entradas de treinamento. A inspeção semântica dos tipos de local encontrou descrições de contexto (como via pública e terminal/estação), não a classificação. Isso reduz vazamento conhecido, mas não demonstra ausência universal de proxies administrativos ou vieses de registro.

Normalização: Unicode NFC, espaços e maiúsculas. Somente {len(pre['treino']['aliases_ativados'])} equivalências explícitas de acentuação, inspecionadas em 2023, são ativadas quando ambas as grafias aparecem no treino. Exemplos: REPÚBLICA/REPUBLICA, BRÁS/BRAS e CONSOLAÇÃO/CONSOLACAO. Não há expansão automática de JD/VL, fusão por similaridade ou união de zonas distintas. Valores de bairro sem nenhuma letra, como códigos numéricos isolados, viram ausentes; não são interpretados como bairros.

O limiar **{config['min_bairro_count']} registros por bairro em 2023** é uma decisão inicial configurável de controle de cardinalidade ({100*config['min_bairro_count']/config['train_rows']:.3f}% do treino), escolhida antes do desempenho da rede e sem busca. Mantém {pre['treino']['bairros_retidos']} bairros frequentes entre {pre['treino']['bairros_observados_treino']} nomes normalizados observados. Os demais formam um bucket estatístico de baixa frequência; **não se afirma que sejam o mesmo bairro**. A tabela de frequências permanece no pré-processador e a fonte permanece intacta. Bairros novos também usam esse bucket; tipos de local novos usam a representação de ausente, já observada no treino. As contagens diagnósticas distinguem novos de ausentes, sem criar indicadores adicionais de origem como entradas.

{table(prep)}

O pré-processador registra ano, quantidade, hash das chaves e hash dos registros de ajuste. Vocabulários, frequência, aliases ativados e categorias raras são aprendidos somente com 2023. A transformação de 2024 não modifica o objeto. A representação é CSR float32; apenas lotes de até 256 linhas são densificados para a MLP. Uma matriz de treino densa completa exigiria aproximadamente {dense_mib:.1f} MiB apenas para entradas; ela não é criada.

## C. Arquitetura

- Entrada: **{config['input_dimension']} dimensões One-Hot**.
- Uma camada oculta Dense(64), ativação ReLU.
- Saída Dense(1), ativação sigmoid: probabilidade estimada de ROUBO.
- **{config['trainable_parameters']:,} parâmetros treináveis**.
- Perda Binary Cross-Entropy; Adam com learning rate 0,001.
- Batch size 256; até 30 épocas; semente 42.
- Early Stopping em `val_loss`, paciência 5, `min_delta=0`, restauração dos melhores pesos.
- Limiar de decisão fixo 0,5; sem otimização de threshold ou pesos de classe.

O ambiente reportado pelo TensorFlow é `{config['tensorflow_devices']}`. CPU lógica: {config['cpu_logical']}; RAM física: {config['ram_gib']:.1f} GiB. Não se presumiu GPU funcional. TensorFlow usa 4 threads intraop e 1 interop; operações determinísticas habilitadas e oneDNN desabilitado para reduzir variação numérica. Reprodutibilidade numérica entre sistemas ou versões diferentes não é garantida.

## D. Treinamento real

Foram realizadas **{config['epochs_ran']} épocas**, em **{config['training_seconds']:.2f} segundos** de `fit`. Melhor época por menor loss de validação: **{best}**. Motivo de parada: `{config['stop_reason']}`. Os pesos salvos são os restaurados da melhor época, não necessariamente os da última linha do histórico. Maior RSS amostrado ao fim de épocas: {peak:.1f} MiB; é uma amostra do processo, não uma medição contínua de pico.

O histórico inclui loss, val_loss, accuracy, val_accuracy, duração e RSS por época, em `etapa2/historico_mlp.csv` e `.json`. Configuração, recursos, versões e hashes estão no arquivo de configuração do modelo. Nenhum hiperparâmetro foi alterado em resposta ao desempenho desta execução.

![Curvas de treinamento](figures/curvas_mlp_baseline.png)

## E. Resultados

As métricas abaixo usam os pesos da melhor época e threshold=0,5. Precision, recall e F1 na tabela resumida referem-se à classe positiva **ROUBO**; Macro F1 e balanced accuracy dão peso igual às duas classes.

{table(rows)}

Métricas por classe:

{table([r for r in classrows if r['ano']==2024])}

![Matrizes de confusão](figures/matriz_confusao_baseline.png)

As linhas da matriz são classes verdadeiras e as colunas são previstas, na ordem FURTO, ROUBO. Distribuição verdadeira versus prevista aparece nas colunas `suporte` e `previsoes`. Não há previsão ou métrica de 2025.

## F. Comparação com a referência

A classe majoritária foi determinada **somente em 2023**: FURTO. A referência sempre prevê FURTO, sem rede neural. Na mesma validação de 2024, sua acurácia é {baseline['accuracy']:.4f}, Macro F1 {baseline['macro_f1']:.4f} e balanced accuracy {baseline['balanced_accuracy']:.4f}; recall de ROUBO é zero. Métricas sem previsões positivas usam `zero_division=0` e são explicitadas como zero, não omitidas.

A MLP obteve diferença de **{diff:+.2f} pontos percentuais de acurácia** e **{f1diff:+.4f} de Macro F1** em relação à referência. O confronto inclui as duas classes e a matriz, em vez de interpretar acurácia isoladamente. A referência não foi ajustada à distribuição de 2024.

## G. Análise crítica e erros

Com os melhores pesos, a diferença de acurácia treino−validação é {100*(train['accuracy']-val['accuracy']):+.2f} pontos percentuais; a diferença de BCE validação−treino é {val['log_loss']-train['log_loss']:+.4f}. No histórico, a melhor val_loss é {history[best-1]['val_loss']:.5f}, e a última é {history[-1]['val_loss']:.5f}. A redução continuada do erro de treino sem melhoria equivalente no erro de validação deve ser tratada como possível sobreajuste; a diferença temporal também pode contribuir. Estas duas causas não são separáveis apenas com uma divisão temporal.

Em 2024, a MLP confunde **{val['matriz_confusao'][0][1]:,} furtos com roubos** e **{val['matriz_confusao'][1][0]:,} roubos com furtos**. O recall por classe acima mostra a assimetria. A prevalência observada muda de {train['por_classe']['ROUBO']['suporte']/train['n']:.4f} de roubos no treino para {val['por_classe']['ROUBO']['suporte']/val['n']:.4f} na validação, além de mudanças de bairros, locais e preenchimento. Não se atribui causalidade ao ano.

Contextos com mais erros absolutos por tipo de local, apenas em grupos com pelo menos 50 exemplos:

{table(top)}

Grupos maiores podem acumular mais erros apenas por volume; compare também `taxa_erro`. O arquivo `etapa2/erros_por_grupo_validacao.csv` contém estratos por mês, dia, local e bairro. Esses diagnósticos são posteriores ao congelamento desta rede e não foram usados para alterar seus hiperparâmetros. Grupos pequenos são omitidos da tabela de desempenho para não superinterpretar taxas instáveis.

Mesmo boa otimização não recupera informação ausente: muitos BOs têm os mesmos quatro atributos e classes diferentes. Um desempenho limitado pode refletir representação insuficiente, ambiguidade do contexto, mudança temporal ou capacidade da arquitetura; esta execução não distingue de forma definitiva underfitting e limite informacional. Ausência de métricas excepcionalmente elevadas não prova ausência de vazamento. Retirar o período reduz o risco conhecido de preenchimento temporal, mas local/bairro ainda podem refletir práticas de registro. A exclusão conservadora de naturezas mistas seleciona parte do universo de celulares e limita generalização.

## H. Artefatos, inferência e testes

- `models/mlp_baseline.keras`: arquitetura, pesos e estado de compilação no formato Keras.
- `models/arquitetura_mlp.json`: arquitetura legível separada.
- `models/preprocessador.joblib`: normalização e vocabulário/frequências ajustados em 2023.
- `models/config_modelo.json`: entradas, tipos, rótulos, hiperparâmetros, execução, versões e proveniência.
- `notebooks/GS_Classificacao_MLP_Completo.ipynb`: notebook executado, com interpretação, resultados e exemplo real de recarga.
- `src/ml/`: dataset, pré-processamento, treinamento, avaliação e interface Python de inferência.
- `reports/tables/metricas_baseline.csv` e `metricas_baseline_por_classe.csv`; figuras acima e diagnósticos em `reports/etapa2/`.
- `docs/etapa2_reproducao.md` e `requirements-ml.txt`: comandos e dependências.

O modelo e o pré-processador foram recarregados e todas as {fail['validation_rows']:,} probabilidades de validação foram comparadas com as anteriores ao salvamento. Diferença absoluta máxima: **{fail['max_abs_difference']:.10f}**, tolerância 1e-7. O teste não acessa 2025. Arquivos joblib devem ser carregados somente de origem local confiável.

Exemplo hipotético de inferência recarregada (mês=5, quarta-feira=2, local=VIA PÚBLICA, bairro=BELA VISTA): `{example}`. Os números são saídas estimadas, **não probabilidades calibradas**, nem risco futuro de crime.

Testes realmente executados:

{table(tests)}

Total: **{ntests} testes**, incluindo os oito originais preservados e os novos testes de ML. Eles verificam alinhamento com falha induzida, temporalidade, chaves disjuntas, quatro entradas permitidas e ausência do período, ajuste só em 2023, não mutação na transformação, ausências, desconhecidos, rótulos, artefatos, recarga e inferência. O carregamento preditivo e o cálculo de métricas rejeitam explicitamente 2025. Manifesto de acesso: `etapa2/acesso_dados.json`. A garantia combina restrições de código e evidência de execução; não é um controle de acesso externo ao processo Python.

Correções de execução: a inspeção inicial usou o nome de API Arrow antigo (`fetch_arrow_table`), corrigido para `sql(...).to_arrow_table()` do DuckDB instalado. Uma sondagem de importação foi iniciada antes de terminar a cópia das dependências e encontrou módulo ainda indisponível; ela foi repetida somente após a instalação terminar. A primeira tentativa de treino parou antes de ajustar a rede devido a um resultado DuckDB ainda não consumido; as consultas de uma linha passaram a ser consumidas integralmente com `fetchall()`. As falhas efetivas do comando de treino ficam em `etapa2/falhas_execucao.log`. Não houve troca silenciosa de arquitetura ou hiperparâmetros.

## I. Recomendações para a Etapa 3

1. Investigar os contextos ambíguos e a assimetria dos erros; não supor que uma rede maior resolva a falta de informação.
2. Verificar estabilidade por mês/local e efeito de categorias novas, ausentes e raras; planejar validação temporal adicional sem abrir 2025.
3. Avaliar futuramente sensibilidade ao limiar de raridade e representações de bairro, com decisões aprendidas só no treino e registradas previamente. Não transformar as tabelas de erro em seleção oportunista de exemplos.
4. Se necessário, investigar calibração e threshold somente em uma partição de desenvolvimento apropriada; os valores atuais continuam fixos e não calibrados.
5. Manter `periodo_fato` fora até uma análise controlada específica de seu mecanismo de preenchimento. Não reintroduzir indicadores administrativos de hora.
6. Planejar a comparação de arquiteturas na etapa autorizada e manter **2025 fechado** até a avaliação final. A Etapa 2 não inclui essa comparação nem desenvolvimento web.

Critérios atendidos: pré-processamento funcional; separação temporal; MLP treinada; métricas e referência; curvas e matriz; persistência e recarga; inferência Python; testes executados; notebook e documentação. Não há pendência operacional se os testes acima estiverem todos aprovados. Permanecem as limitações científicas de domínio, ambiguidade, proxies e calibração descritas. **O desenvolvimento termina na Etapa 2.**
'''
    # Acrescenta evidência específica de erros de treinamento reais, se presentes.
    if (OUT/'falhas_execucao.log').exists():
        text+='\nHá registro de falhas anteriores em `etapa2/falhas_execucao.log`; consulte também as decisões de reprodução para as correções.\n'
    (ROOT/'reports/relatorio_etapa2.md').write_text(text,encoding='utf-8')
    notebook(config,metrics,pre)
    print(text,flush=True)

def notebook(config,metrics,pre):
    """Navegação atual; a reprodução original permanece no histórico Git."""
    path = ROOT/'notebooks/GS_Classificacao_MLP_Completo.ipynb'
    print('Notebook acadêmico consolidado:', path)
    return path

if __name__=='__main__':report()
