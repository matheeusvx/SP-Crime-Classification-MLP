"""Relatorio academico, recomendacoes e notebook; nunca executa novos treinos."""
from experiments4.common import *
from experiments4.comparison import runs
import numpy as np,io,contextlib,uuid
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

FIG=OUT/'figuras'
def rows(name):
    with (OUT/(name+'.csv')).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def table(records,cols=None):
    if not records:return '(sem linhas)'
    cols=cols or list(records[0]);fmt=lambda v:f'{v:.5f}' if isinstance(v,float) else str(v)
    return '| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+'\n'.join('| '+' | '.join(fmt(r.get(c,'')) for c in cols)+' |' for r in records)

def figures(rs):
    FIG.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    ar=[next(r for r in rs if r['run_id']==f'{id}_internal_s42') for id in ['B32','B64','B64_32']]
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    for r,color in zip(ar,['#126C8A','#DB7E22','#62783D']):
        h=r['history'];x=range(1,len(h['loss'])+1)
        for ax,k in [(axes[0],'loss'),(axes[1],'accuracy')]:
            ax.plot(x,h[k],color=color,label=r['id']+' treino')
            ax.plot(x,h['val_'+k],color=color,ls='--',label=r['id']+' validação')
    for ax in axes:ax.set_xlabel('Época');ax.legend(fontsize=8)
    axes[0].set_title('BCE');axes[1].set_title('Acurácia');fig.suptitle('Três arquiteturas · Treino Jan–Set/2023 e validação Out–Dez/2023')
    fig.savefig(FIG/'curvas_arquiteturas.png',dpi=150);plt.close(fig)
    a=rows('comparacao_atributos');fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for ax,key,title in [(axes[0],'macro_f1','Macro F1'),(axes[1],'recall_roubo','Recall de roubo')]:
        ax.bar([r['id'] for r in a],[float(r[key]) for r in a],color='#126C8A');ax.set_ylim(0,1);ax.set_title(title);ax.tick_params(axis='x',rotation=30)
    fig.suptitle('Ablações e bairros raros · Somente validação interna de 2023');fig.savefig(FIG/'comparacao_atributos.png',dpi=150);plt.close(fig)
    b=rows('comparacao_arquiteturas');fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    x=np.arange(len(b));axes[0].bar(x-.17,[float(r['macro_f1']) for r in b],.34,label='Macro F1');axes[0].bar(x+.17,[float(r['recall_roubo']) for r in b],.34,label='Recall roubo')
    axes[0].set_xticks(x,[r['architecture'] for r in b]);axes[0].legend();axes[0].set_ylim(.5,.75);axes[0].set_xlabel('Camadas ocultas')
    axes[1].bar([r['architecture'] for r in b],[int(r['parameters']) for r in b],color='#126C8A');axes[1].set_ylabel('Parâmetros treináveis')
    fig.suptitle('Comparação 2024 · Semente 42 · Três épocas fixadas internamente');fig.savefig(FIG/'comparacao_arquiteturas.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,4),layout='constrained')
    for ax,r in zip(axes,[next(r for r in rs if r['run_id']==f'{id}_full_s42') for id in ['B32','B64','B64_32']]):
        m=r['validation_metrics'];cm=np.array([[m['tn'],m['fp']],[m['fn'],m['tp']]])
        ax.imshow(cm,cmap='Blues',vmin=0,vmax=92055)
        for i in range(2):
            for j in range(2):ax.text(j,i,f'{cm[i,j]:,}'.replace(',','.'),ha='center',va='center')
        ax.set_xticks([0,1],['FURTO','ROUBO']);ax.set_yticks([0,1],['FURTO','ROUBO']);ax.set_title(r['id']);ax.set_xlabel('Previsto')
    axes[0].set_ylabel('Verdadeiro');fig.suptitle('Matrizes de confusão · Validação 2024 · Semente 42');fig.savefig(FIG/'matrizes_2024.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained');st=rows('estabilidade')
    for ax,metric,title in [(axes[0],'macro_f1','Macro F1'),(axes[1],'recall_roubo','Recall de roubo')]:
        r=[s for s in st if s['scope']=='full' and s['metric']==metric]
        ax.bar([v['id'] for v in r],[float(v['mean']) for v in r],yerr=[float(v['sd']) for v in r],capsize=5,color='#126C8A');ax.set_ylim(.5,.75);ax.set_title(title)
    fig.suptitle('Validação 2024 · Média ± DP amostral · Sementes 42, 7 e 123');fig.savefig(FIG/'estabilidade_sementes.png',dpi=150);plt.close(fig)
    reg=rows('comparacao_regularizacao');fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for ax,key,title in [(axes[0],'macro_f1','Macro F1 interna'),(axes[1],'gap_bce','BCE validação − treino')]:
        ax.bar([r['id'] for r in reg],[float(r[key]) for r in reg],color='#126C8A');ax.set_title(title);ax.tick_params(axis='x',rotation=15)
    fig.suptitle('Regularização · Mesmo Dense64 e mesmos dados internos');fig.savefig(FIG/'regularizacao.png',dpi=150);plt.close(fig)
    full=[r for r in rs if r['scope']=='full' and r['seed']==42]
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for r in full:
        for ax,k in [(axes[0],'loss'),(axes[1],'accuracy')]:ax.plot(range(1,len(r['history'][k])+1),r['history'][k],label=r['id'])
    for ax in axes:ax.legend();ax.set_xlabel('Época fixa')
    axes[0].set_title('Loss de treino completo');axes[1].set_title('Acurácia de treino completo')
    fig.suptitle('Reajuste 2023 · Sem monitoramento de 2024 por época');fig.savefig(FIG/'curvas_reajuste.png',dpi=150);plt.close(fig)

def generate():
    preserve();rs=runs();figures(rs)
    a=rows('comparacao_atributos');b=rows('comparacao_arquiteturas');reg=rows('comparacao_regularizacao');summary=rows('resumo_validacao_2024');st=rows('estabilidade');tests=read('testes.json');rec=read('recomendacao_candidatos.json');decision=read('decisao_representacao.json')
    main=rec['principal'];alt=rec['alternativa'];ntests=sum(r['executados'] for r in tests);count=rec['experiment_counts']
    # Mesmos grupos da Etapa 3, definidos com o treino completo, sem bairros individuais.
    important=[]
    for id in ['A0','A1','B32','B64','B64_32']:
        r=next(r for r in rs if r['run_id']==f'{id}_full_s42')
        for g in r['groups']:
            if g['grupo'] in ['bairro_referencia_50','presenca_local']:
                important.append({'id':id,'grupo':g['grupo'],'categoria':g['categoria'],**{k:g[k] for k in ['n','fp','fn','macro_f1','balanced_accuracy','recall_roubo','fpr','high_conf_errors']}})
    save('erros_persistentes_resumo',important)
    historical=json.loads((ROOT/'reports/etapa2/metricas_baseline.json').read_text(encoding='utf-8'));hist=next(r for r in historical if r['modelo']=='MLP' and r['ano']==2024)
    errors=[{'id':'Historico','n':hist['n'],'fp':hist['matriz_confusao'][0][1],'fn':hist['matriz_confusao'][1][0],'high_conf_errors':879,'brier':.2009063087680951,'log_loss':hist['log_loss']}]
    errors.extend({'id':r['id'],**{k:r['validation_metrics'][k] for k in ['n','fp','fn','high_conf_errors','brier','log_loss']}} for r in rs if r['scope']=='full' and r['seed']==42)
    save('erros_vs_historico',errors)
    monthly=[{'id':r['id'],**g} for r in rs if r['scope']=='full' and r['seed']==42 for g in r['groups'] if g['grupo']=='mes'];save('desempenho_mensal_2024',monthly)
    candidate_models=[{'id':id,'role':role,'result':f'reports/etapa4/runs/{id}_full_s42.json','model':next(r['model_path'] for r in rs if r['run_id']==f'{id}_full_s42'),
      'preprocessor':next(r['preprocessor_path'] for r in rs if r['run_id']==f'{id}_full_s42')} for id,role in [(main['id'],'candidata principal, nao definitiva'),(alt['id'],'alternativa: mais recall, mais falsos positivos'),('B32','alternativa compacta exploratoria, somente uma semente completa')]]
    json_write(OUT/'candidatos_artefatos.json',candidate_models)
    facts=[
      {'id':'A0','interpretacao':'Referencia sob novo protocolo; nao substitui historico.'},
      {'id':'A1','interpretacao':'Retirar local reduz Macro F1 e recall gerais; melhora parte dos roubos sem local. Dependencia nao prova seguranca do atributo.'},
      {'id':'A2','interpretacao':'Retirar bairro causa a maior perda interna; recall sobe a custa de muitos falsos positivos. Nao avancou a 2024.'},
      {'id':'A3','interpretacao':'Pequeno ganho interno de Macro F1 com perda de 3,88 pp de recall; nao escolhido. Meses Q4 nao vistos limitam interpretacao.'},
      {'id':'A4_10','interpretacao':'Maior dimensao e menos raros; ganho de Macro F1 ~0,057 pp, sem ganho claro e recall menor. Nao avancou.'},
      {'id':'A4_100','interpretacao':'Menor dimensao; perde ~0,140 pp de Macro F1 interna. Sem beneficio preditivo demonstrado.'},
      {'id':'A5','interpretacao':'Matrizes identicas a A0; reutilizacao comprovada. Melhora somente contrato de acentuacao, sem ganho metrico alegado.'},
      {'id':'B32','interpretacao':'Mais simples; desempenho 2024 proximo de B64 e do historico, mas apenas uma semente completa.'},
      {'id':'B64','interpretacao':'Mais estavel entre as candidatas; preserva capacidade historica e nao demonstra ganho de Macro F1 sobre o historico.'},
      {'id':'B64_32','interpretacao':'Mais recall, mais FP e maior complexidade; nenhum ganho consistente de Macro F1.'},
      {'id':'C_dropout','interpretacao':'Macro F1 quase igual, recall maior, mas BCE de validacao e gap piores; nao melhorou generalizacao no ensaio interno.'},
      {'id':'C_l2','interpretacao':'Gap BCE menor, sem melhorar Macro F1 ou BCE de validacao; reduzir gap isoladamente nao demonstra beneficio.'}]
    save('interpretacao_configuracoes',facts)
    failures=[]
    if (OUT/'falhas.jsonl').exists():failures=[json.loads(line) for line in (OUT/'falhas.jsonl').read_text(encoding='utf-8').splitlines() if line]
    recommendation=f'''# Recomendações para a Etapa 5

Não há vencedor definitivo. Nenhum dado de 2025 foi avaliado nesta etapa. Há **ganho limitado**, e não evidência de que mais capacidade resolva a tarefa.

## Candidatas e evidências

- Principal experimental: **{main['id']} / Dense64**, quatro atributos, limiar50, alias inequívoco de acentuação de local. Três épocas fixas escolhidas internamente. Média de três sementes: Macro F1={main['macro_f1_mean']:.5f} (DP {main['macro_f1_sd']:.5f}), balanced accuracy={main['balanced_accuracy_mean']:.5f}, recall roubo={main['recall_roubo_mean']:.5f}. Diferença de Macro F1 contra histórico: {main['macro_delta_historico_pp']:+.3f} pp; não é ganho comprovado.
- Alternativa com prioridade em recall: **{alt['id']} / Dense64→32**, Macro F1={alt['macro_f1_mean']:.5f}, recall={alt['recall_roubo_mean']:.5f}; mais FP e parâmetros. Só faz sentido se esse compromisso for aceito; profundidade não produziu melhoria geral.
- Alternativa compacta: **B32**, 9.633 parâmetros. Macro F1 de uma semente completa ~0,67745, próximo dos demais. Não se pode afirmar superioridade ou estabilidade com uma semente; sua simplicidade merece consideração, sem acrescentar tentativas nesta etapa após ver 2024.
- Preservar o baseline histórico como opção de referência: Macro F1 0,67766, com EarlyStopping em 2024. Seu protocolo difere e a vantagem numérica pequena não é comparação imparcial de otimização.

## Antes de abrir 2025

1. Fixar a configuração final e o tratamento de ausências/novos/acentuação. Não transformar OUTROS em ausente; a relação de local com coleta continua sem confirmação semântica externa. A ablação mostra dependência e troca de erros, não prova causalidade ou ausência de vazamento.
2. Revisar a robustez dos buckets raros: mesmo com quatro atributos e limiar50, raros/novos seguem com FPR alto. Não inferir risco de bairros. Mudanças de representação adicionais exigem protocolo de desenvolvimento explícito e não usar 2025.
3. Decidir o orçamento final sem ajustá-lo ao teste. O recorte Jan–Set vs Q4 contém meses não observados no treino; três épocas foram uma escolha conservadora e podem limitar o reajuste. Não recomendar mais épocas apenas porque o histórico usou cinco e teve métrica ligeiramente maior.
4. Se calibrar ou escolher threshold, separar ajuste e verificação em dados de desenvolvimento; não usar os mesmos exemplos para afirmar melhoria imparcial. Os três epochs refits têm ECE/Brier que não superam consistentemente o histórico. Manter 0,5 até esse protocolo ser aprovado. Probabilidades não são risco futuro de crime.
5. Critérios finais: Macro F1 principal, balanced accuracy, recall/precision por classe, FP/FN, Brier/Log Loss, confiabilidade por suporte, grupos ausentes/raros/novos e custo. Não escolher pela melhor semente. Definir também os custos de FP/FN, hoje não fornecidos.
6. Após congelar modelo/pré-processador/threshold e protocolo de calibração, avaliar 2025 **uma única vez** para estimativa final. Não resolver empates nem refazer arquitetura com base nesse resultado. A Etapa 5 depende de autorização do usuário.

Artefatos por candidato: `reports/etapa4/candidatos_artefatos.json`. Todos os checkpoints e preprocessadores estão em `models/experiments/etapa4/`, sem promover qualquer arquivo a `mlp_baseline.keras`.
'''
    (ROOT/'docs/recomendacoes_etapa5.md').write_text(recommendation,encoding='utf-8')
    text=f'''# Etapa 4 — Experimentação controlada e comparação de MLPs

## Escopo e protocolo

O domínio continua sendo BOs elegíveis com celulares subtraídos na capital; 0=FURTO, 1=ROUBO. Nenhuma previsão de crime futuro, aplicação web, calibrador ou avaliação de 2025 foi realizada. Artefatos anteriores preservados por SHA256: **{preserve()} arquivos**. As configurações originais, seus relatórios e seus 40 testes foram mantidos.

Matriz registrada antes de treinar: [matriz experimental](etapa4/matriz_planejada.json); [protocolo](../docs/protocolo_experimental_etapa4.md). São **{count['logical_runs']} registros de execução**, **{count['fresh_trainings']} treinamentos novos** e **{count['reused']} reutilizações comprovadas** (A5 a partir de A0; B64 interno a partir de A5). Falhas efetivas registradas: **{len(failures)}**, em `falhas.jsonl` se houver. Configurações inferiores permanecem nas tabelas.

Treinamento interno: **144.697 BOs de janeiro–setembro/2023**, 81.128 furtos e 63.569 roubos. Validação interna: **45.427 de outubro–dezembro/2023**, 25.293 furtos e 20.134 roubos. Chaves únicas/disjuntas; ajuste de frequências/vocabulários somente no treino correspondente. Antes de B foram definidos os atributos; antes de 2024, candidatos e agenda completa foram congelados em `agenda_reajuste_congelada.json`.

Depois, os preprocessadores foram reajustados em **190.124 BOs de todo 2023**, com comparação em **158.895 de 2024**. Todas as redes reajustadas usaram **três épocas fixas**, escolhidas pela melhor época interna ou mediana das três sementes internas, sem monitorar 2024 por época. A limitação já conhecida de 2024 ter sido consultado em etapas anteriores permanece: ele é desenvolvimento/seleção, não teste independente. 2025 permanece reservado. Os testes legados usam metadados/hashes apenas para integridade.

Mês/dia recebem One-Hot nominal do domínio fixo do calendário, sem estatísticas do holdout. No recorte interno, meses 10/11/12 não têm exemplos de treinamento; seus pesos não aprendem efeitos. Isso limita a inferência sobre mês e a escolha de épocas, e não é vazamento nem justificativa para usar 2024 no orçamento. Bairros/local, frequências, aliases ativados e demais categorias vêm só do treino. Não há natureza, identificadores, período, indicadores extras de ausência ou dados pessoais nas entradas.

## A. Atributos e pré-processamento

Mesma Dense64, semente42, Adam0,001, batch256, BCE, ReLU/sigmoid, máximo30 épocas, EarlyStopping interno em val_loss com paciência5 e restauração dos melhores pesos. Threshold0,5. Os limites de frequência10/50/100 são definidos sem usar y. Ausências não removem BOs; desconhecidos mantêm fallbacks explícitos. CSR float32 é densificado apenas por lote.

{table(a,['id','input_dimension','parameters','retained_bairros','train_rare_bucket','validation_rare_bucket','validation_unknown_bairros','macro_f1','balanced_accuracy','recall_roubo','fp','fn','delta_macro_f1_pp','training_seconds'])}

{table([r for r in facts if r['id'].startswith('A')])}

**A1:** perda interna de ~3,31 pp de Macro F1 ao retirar local, mas isso não prova que local seja um atributo seguro. A comparação completa em 2024 também foi prevista para investigar os 479 roubos sem local. **A2:** a maior perda é sem bairro (~10,22 pp de Macro F1), com recall alto obtido por muitos FP; não se deve confundir recall isolado com ganho. **A3:** ganho de apenas +0,134 pp de Macro F1 com −3,879 pp de recall frente a A0. **A4:** 10 amplia dimensão267→671 e parâmetros17.217→43.073, sem ganho claro; 100 reduz dimensão para205 e perde um pouco de desempenho. São resultados de uma semente interna, não conclusões universais sobre os limiares.

**A5:** categorias de local foram revistas semanticamente nas etapas anteriores e no vocabulário de treino: a nova regra só reconhece equivalência de acentuação com correspondência unívoca a um nome visto. OUTROS e ausente continuam distintos; não houve inferência de recodificação entre anos. A0 e A5 têm matrizes codificadas idênticas em treino e validação interna; os pesos foram reutilizados, não retreinados, e não se alega ganho de métrica. `VIA PUBLICA` agora corresponde a `VIA PÚBLICA` no experimento, preservando o contrato histórico em seus próprios arquivos.

Decisão antes de B: **quatro atributos, frequência mínima50 e A5**. O desempate mecânico registrado na matriz apontou A3; houve revisão qualitativa documentada, porque o usuário exigiu não sacrificar substancialmente o recall por diferença mínima de Macro F1. A revisão ocorreu antes de B e de 2024, sem acrescentar tentativas. É uma intervenção de julgamento no desempate, não uma regra totalmente automática pré-registrada. A configuração original continua disponível.

![Ablações](etapa4/figuras/comparacao_atributos.png)

## B. Comparação das três arquiteturas

Representação fixa A5 em todas. `comparacao_arquiteturas.csv` abaixo usa a mesma semente42 e os mesmos registros de 2024; todas têm299 entradas, três épocas fixas, threshold0,5 e nenhum ajuste em 2024. Valores em escala0–1, e deltas em pontos percentuais.

{table(b,['id','architecture','parameters','epochs','training_seconds','accuracy','precision_roubo','recall_roubo','f1_roubo','precision_furto','recall_furto','macro_f1','balanced_accuracy','brier','log_loss'])}

A tabela completa inclui melhor época interna, loss/accuracy, suporte, matriz, tempos, dimensões e hashes. 32, 64 e 64→32 foram efetivamente treinadas. A opcional128→64 foi omitida conforme orçamento prévio para priorizar regularização e evitar capacidade adicional sem hipótese forte.

![Curvas internas](etapa4/figuras/curvas_arquiteturas.png)
![Comparação e parâmetros](etapa4/figuras/comparacao_arquiteturas.png)
![Matrizes](etapa4/figuras/matrizes_2024.png)
![Curvas de reajuste](etapa4/figuras/curvas_reajuste.png)

As curvas com treino/validação são as internas de 2023. As curvas de reajuste completo mostram somente treino; 2024 foi avaliado após as três épocas, sem curvas de validação por época que pudessem orientar nova seleção do orçamento.

## C. Regularização e hiperparâmetros

Arquitetura de referência interna escolhida: Dense64. Dropout0,1 e L2=0,0001 foram testados separadamente; o restante permaneceu fixo. Com L2, o loss monitorado contém a penalidade; a BCE sem penalidade é calculada separadamente para comparação. Não interpretar a diferença de loss penalizado como diferença direta de qualidade probabilística.

{table(reg,['id','macro_f1','balanced_accuracy','recall_roubo','brier','log_loss','train_bce','gap_bce','best_epoch','epochs','training_seconds'])}

Dropout não melhorou a Macro F1 e aumentou o gap de BCE. L2 reduziu o gap, mas não melhorou a BCE de validação nem Macro F1. Menor gap isolado não comprova melhor generalização. Nenhum regularizado avançou a reajuste em2024. O gatilho prévio para learning rate0,0005 não ocorreu (quatro variações consecutivas de val_loss superiores a0,01); portanto não houve essa tentativa. Dropout0,2 e busca exaustiva não foram executados.

![Regularização](etapa4/figuras/regularizacao.png)

## D. Estabilidade e comparação com o histórico

As duas configurações escolhidas internamente foram B64 e B64→32. Três sementes globais42/7/123, mantendo a ordem dos lotes RNG42. O determinismo TensorFlow está habilitado, CPU, threads4/1 e oneDNN desabilitado; ambiente e versões em `ambiente.json`. As sementes alteram inicialização e fontes aleatórias da rede, não a partição ou frequências. Não se escolheu a melhor semente para a recomendação.

{table([r for r in st if r['metric'] in ['macro_f1','recall_roubo']])}

![Estabilidade](etapa4/figuras/estabilidade_sementes.png)

Resumo de2024, usando média quando há três sementes:

{table(summary,['id','architecture','n_seeds','parameters','accuracy_mean','macro_f1_mean','macro_f1_sd','balanced_accuracy_mean','recall_roubo_mean','precision_roubo_mean','brier_mean','macro_delta_historico_pp'])}

Baseline histórico: accuracy0,68728; Macro F1 0,67766; balanced accuracy0,67692; recall roubo0,61158. **O histórico usou2024 em EarlyStopping e restaurou época5; os novos modelos usam3 épocas sem EarlyStopping em2024.** A0 refaz a arquitetura original pelo protocolo novo e serve à comparação mais equivalente; A0 e B64 s42 produzem resultados iguais nos dados existentes, pois A5 muda apenas variantes de inferência, não as matrizes observadas.

Dense64 tem média de Macro F1 {main['macro_f1_mean']:.5f}, DP {main['macro_f1_sd']:.5f}, diferença {main['macro_delta_historico_pp']:+.3f} pp do histórico. A rede profunda tem média {alt['macro_f1_mean']:.5f}, maior recall e mais FP. Não há ganho consistente de Macro F1 sobre o histórico. A compacta32 aproxima esses resultados com metade dos parâmetros, mas só tem uma semente de reajuste; nenhuma nova tentativa foi acrescentada após ver2024. Diferenças mínimas, protocolos distintos e três sementes não sustentam alegações fortes de superioridade.

## E. Erros persistentes, probabilidades e robustez

Comparação semente42 com histórico:

{table(errors)}

Os reajustes reduzem erros com confiança≥90%, mas ainda falham; isso pode refletir menor treinamento/confiança, não calibração comprovadamente melhor. Brier/Log Loss não superam consistentemente o histórico. Todas as probabilidades continuam sem calibrador e threshold0,5. Não foram escolhidos limiares individuais para favorecer redes.

Grupos com as mesmas definições da Etapa3 para a referência de frequência50:

{table([r for r in important if r['id'] in ['A0','A1','B64','B64_32'] and (r['grupo']=='presenca_local' or r['categoria'] in ['raro_conhecido','desconhecido'])])}

Nos 4.653 BOs sem local, A1 reduz os FN de479 para190 (recall de roubo 0%→60,33%), mas introduz **1.342 FP** entre4.174 furtos (FPR32,15%). Portanto, o atributo condiciona fortemente o padrão de erros e sua retirada troca erros, sem resolver a tarefa. A queda do desempenho geral ao remover local não elimina o risco de proxy administrativo. Em bairros raros/novos, A1 prevê ROUBO para todos os registros desses grupos: recall100% e FPR100%, evidência clara de que recall isolado seria enganoso.

Raros/novos continuam com elevada assimetria, mesmo nos candidatos: no B64 s42, 3.838 FP e348 FN entre12.673 raros conhecidos, FPR75,46%; entre355 novos, 92 FP e10 FN, FPR70,77%. Os grupos têm prevalências diferentes; as taxas não são rankings de segurança. Suporte mínimo de destaque: n≥200 e pelo menos30 exemplos de cada classe. Há apenas355 registros com bairros desconhecidos em2024; conclusões sobre cada nome isolado seriam frágeis.

`erros_subgrupos.csv` inclui todos os experimentos, grupos de referência50 e grupos próprios de cada limiar. Os de referência mantêm as mesmas populações para comparar limiares; os próprios mudam de composição e não devem ser comparados ingenuamente. `desempenho_mensal_2024.csv` registra estabilidade temporal com suportes e recalls. `resultados_experimentos.csv` contém gaps entre treino e validação, Brier/Log Loss e ECE10. A interação com coleta não foi transformada em causalidade.

A nova equivalência de acentuação de local é testada sem fundir OUTROS ou locais diferentes. Categorias desconhecidas e ausências têm fallback; limitações temporais e de bairros ainda existem. Dados com o mesmo contexto podem ter rótulos diferentes; mais parâmetros não recuperam informação ausente. O teto empírico da Etapa3 é retrospectivo da amostra, não limite matemático universal.

## F. Artefatos, testes e reprodução

{table(tests)}

**{ntests} testes executados**, com os40 anteriores preservados. Verificações incluem partições e alinhamento, chaves, dados de ajuste, ausência de2025, entradas permitidas, hashes, compatibilidade/recarregamento de modelos, categorias novas, reprodução das métricas a partir das previsões, configuração estável entre sementes e integridade das tabelas. O carregador preditivo bloqueia2025; os testes antigos usam apenas verificações de integridade sobre seus metadados/hashes, sem predição ou métricas.

Artefatos locais: `models/experiments/etapa4/<run>/modelo.keras`, `preprocessador.joblib`, `config.json` e previsões locais em `.npz`, ignoradas pelo Git. Cada execução guarda configuração, assinatura, data UTC, versão dos dados por SHA256, sementes, épocas, tempo, histórico, métricas e caminhos. `runs/*.json` e `eventos.jsonl` preservam rastreabilidade; cache valida configuração e hashes antes de reutilizar. Relatórios públicos contêm agregados, sem BOs/identificadores ou exemplos reais individuais.

Reprodução, com o ambiente ML já configurado, PYTHONPATH=src e PYTHONHASHSEED=42:

```powershell
python -m experiments4.plan
python -m experiments4.run A
python -m experiments4.run BC
python -m experiments4.run refit
python -m experiments4.comparison
python -m experiments4.run_tests
python -m experiments4.report
```

Execuções válidas em cache não são retreinadas. O notebook `notebooks/GS_Classificacao_MLP_Completo.ipynb` lê resultados e gráficos, sem disparar a bateria. As decisões são salvas entre blocos, antes do próximo nível. Ao reproduzir A, a revisão qualitativa do recall descrita no protocolo é aplicada de forma explícita e registrada.

## G. Candidatas para a Etapa5 — sem seleção definitiva

{table(candidate_models)}

{recommendation}

O resultado acadêmico é uma comparação controlada com **benefício limitado de capacidade e regularização**, não uma promessa de aumento de acurácia. O baseline histórico, datasets e documentos anteriores continuam intactos. **2025 não foi avaliado. O desenvolvimento termina na Etapa4.**
'''
    (ROOT/'reports/relatorio_etapa4.md').write_text(text,encoding='utf-8');notebook();preserve();print(text,flush=True)

def notebook():
    """Navegação atual; a reprodução original permanece no histórico Git."""
    path = ROOT/'notebooks/GS_Classificacao_MLP_Completo.ipynb'
    print('Notebook acadêmico consolidado:', path)
    return path

if __name__=='__main__':generate()
