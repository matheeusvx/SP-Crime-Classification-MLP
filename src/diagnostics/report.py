"""Figuras, interpretacao A–I, recomendacoes e notebook executado da Etapa 3."""
from diagnostics.common import *
import io,contextlib,uuid
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def rows(name):
    with (OUT/(name+'.csv')).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def table(rs,cols=None):
    if not rs:return '(sem linhas)'
    cols=cols or list(rs[0]);fmt=lambda v:f'{v:.5f}' if isinstance(v,float) else str(v)
    return '| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+'\n'.join('| '+' | '.join(fmt(r.get(c,'')) for c in cols)+' |' for r in rs)

def plots():
    FIG.mkdir(parents=True,exist_ok=True);plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    m=read('resumo.json')['validacao'];fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
    ax.bar(['Furtos → roubos (FP)','Roubos → furtos (FN)'],[100*m['fp']/m['furtos'],100*m['fn']/m['roubos']],color=['#126C8A','#DB7E22'])
    for i,(count,den) in enumerate([(m['fp'],m['furtos']),(m['fn'],m['roubos'])]):ax.text(i,100*count/den+1,f'{count:,} / {den:,}\n{100*count/den:.2f}%',ha='center')
    ax.set_ylim(0,50);ax.set_ylabel('% da classe verdadeira');ax.set_title('Validação 2024 · Taxas de erro por classe')
    fig.savefig(FIG/'erros_por_classe.png',dpi=150);plt.close(fig)
    temporal=sorted([g for g in rows('metricas_grupos') if g['atributo']=='mes'],key=lambda r:int(r['categoria']))
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained');x=[int(r['categoria']) for r in temporal]
    for k,label in [('accuracy','Acurácia'),('macro_f1','Macro F1'),('balanced_accuracy','Balanced accuracy'),('recall_roubo','Recall roubo')]:axes[0].plot(x,[float(r[k]) for r in temporal],label=label,marker='o',ms=3)
    axes[0].set_xticks(x);axes[0].set_xlabel('Mês do fato · 2024');axes[0].legend();axes[0].set_ylim(.5,.8)
    axes[1].bar(x,[int(r['n']) for r in temporal],color='#126C8A');axes[1].set_xlabel('Mês do fato · 2024');axes[1].set_ylabel('Boletins');axes[1].set_xticks(x)
    fig.suptitle('Estabilidade mensal do baseline congelado');fig.savefig(FIG/'desempenho_temporal.png',dpi=150);plt.close(fig)
    # Usa somente predicoes preexistentes de validacao, ja reproduzidas nesta etapa.
    npz=np.load(ROOT/'reports/etapa2/validacao_predicoes.npz');p=npz['prob_roubo'];y=npz['y_true'];correct=(p>=.5)==y
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    for label,color in [(0,'#126C8A'),(1,'#DB7E22')]:axes[0].hist(p[y==label],bins=np.linspace(0,1,21),histtype='step',lw=2,label='FURTO verdadeiro' if label==0 else 'ROUBO verdadeiro',color=color)
    for mask,label in [(correct,'Corretos'),(~correct,'Incorretos')]:axes[1].hist(np.maximum(p[mask],1-p[mask]),bins=np.linspace(.5,1,21),histtype='step',lw=2,label=label)
    axes[0].set_xlabel('P(ROUBO) estimada');axes[1].set_xlabel('Confiança na classe prevista');
    for ax in axes:ax.legend();ax.set_ylabel('Boletins')
    fig.suptitle('Probabilidades e confiança · Validação 2024');fig.savefig(FIG/'distribuicao_confianca.png',dpi=150);plt.close(fig)
    bins=[r for r in rows('calibracao_bins') if r['bins']=='10' and int(r['n'])>0]
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained');a=axes[0]
    a.plot([0,1],[0,1],'--',color='gray',label='Referência ideal');a.plot([float(r['prob_media']) for r in bins],[float(r['freq_roubo']) for r in bins],'o-',color='#126C8A',label='Baseline')
    a.set_xlabel('P(ROUBO) média no intervalo');a.set_ylabel('Frequência observada de ROUBO');a.legend()
    axes[1].bar([float(r['inferior'])+.05 for r in bins],[int(r['n']) for r in bins],width=.09,color='#126C8A');axes[1].set_xlabel('Intervalo de P(ROUBO)');axes[1].set_ylabel('Suporte')
    fig.suptitle('Confiabilidade diagnóstica · 10 intervalos de largura 0,1');fig.savefig(FIG/'curva_calibracao.png',dpi=150);plt.close(fig)
    ts=rows('limiares_diagnosticos');fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for k,label in [('precision_roubo','Precision'),('recall_roubo','Recall'),('f1_roubo','F1')]:axes[0].plot([float(r['limiar']) for r in ts],[float(r[k]) for r in ts],label=label)
    axes[0].axvline(.5,color='gray',ls='--');axes[0].set_xlabel('Limiar diagnóstico');axes[0].legend()
    axes[1].plot([float(r['recall_roubo']) for r in ts],[float(r['precision_roubo']) for r in ts],'o-');axes[1].set_xlabel('Recall ROUBO');axes[1].set_ylabel('Precision ROUBO')
    fig.suptitle('Compromisso precision–recall · Limiar operacional permanece 0,5');fig.savefig(FIG/'precision_recall_limiares.png',dpi=150);plt.close(fig)
    imp=rows('importancia_atributos');fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
    ax.barh([r['atributo'] for r in imp],[100*float(r['delta_macro_f1_media']) for r in imp],xerr=[100*float(r['delta_macro_f1_dp']) for r in imp],color='#126C8A');ax.set_xlabel('Queda de Macro F1 · pontos percentuais');ax.set_title('Permutação agrupada · Média ± DP de 5 repetições\nAmostra fixa de 30 mil BOs de 2024; não causal')
    fig.savefig(FIG/'importancia_atributos.png',dpi=150);plt.close(fig)

def generate():
    preserve()
    save('metricas_grupos',[r for r in rows('metricas_grupos') if r['atributo']!='bairro' or r['destacar']=='True'])
    plots();s=read('resumo.json');m=s['validacao'];groups=rows('metricas_grupos');conf=rows('confianca');imp=rows('importancia_atributos');tests=read('testes.json')
    missing=rows('ausencias_ano_classe');localmissing=[r for r in missing if r['atributo']=='tipo_local'];conditions=[r for r in groups if r['atributo']=='condicao_bairro']
    temporal=sorted([r for r in groups if r['atributo']=='mes'],key=lambda r:int(r['categoria']));stability=[read(f'estabilidade_{seed}.json') for seed in [42,7,123]]
    incorrect=next(r for r in conf if r['grupo']=='incorretos');hist=json.loads((ROOT/'reports/etapa2/historico_mlp.json').read_text(encoding='utf-8'));best=hist[4];last=hist[-1]
    ntests=sum(t['executados'] for t in tests);originals=preserve()
    # Sondagens sinteticas publicas, sem registros individuais da base.
    from ml.inference import ClassificadorOcorrencias
    clf=ClassificadorOcorrencias();probe=[]
    for name,args in [('valido',(5,2,'VIA PÚBLICA','BELA VISTA')),('minusculas',(5,2,'via pública','bela vista')),('local_sem_acento',(5,2,'VIA PUBLICA','BELA VISTA')),('local_novo',(5,2,'LOCAL NOVO','BELA VISTA')),('ausentes',(None,None,None,None)),('bairro_codigo_textual',(5,2,'VIA PÚBLICA','152'))]:
        probe.append({'caso_sintetico':name,**clf.classificar(*args)})
    save('sondagens_inferencia',probe)
    recommendation=[
      {'prioridade':1,'problema':'Possivel proxy administrativo de tipo_local','evidencia':'Ausencia por classe desigual; OUTROS 12→7706; todos os 479 roubos com local ausente viram FN','hipotese':'Parte do ganho pode refletir coleta/recodificacao, alem do contexto do fato','experimento':'Ablacao controlada com/sem tipo_local e comparacao por preenchimento, em dobras temporais de desenvolvimento','metrica':'Macro F1, balanced accuracy, recall de roubo e FPR por grupo/mes','impacto_limitacoes':'Avalia dependencia do atributo; perda preditiva nao prova que a informacao era vazamento'},
      {'prioridade':2,'problema':'Bucket raro compartilha representacao com bairros novos','evidencia':'Raros conhecidos: recall roubo ~95%, FPR ~75%; desconhecidos n=355 em 247 nomes','hipotese':'O bucket aprende a mistura de classes e perde heterogeneidade geografica','experimento':'Poucos limiares de frequencia predefinidos; vocabulario normalizado auditado; futuramente embedding com regularizacao','metrica':'Macro F1, recall por classe, FPR, Brier por condicao de bairro e estabilidade temporal','impacto_limitacoes':'Pode reduzir assimetria; embedding exige controle de capacidade e mais validacao; nao cria informacao ausente'},
      {'prioridade':3,'problema':'Val_loss piora apos epoca 5 com train_loss em queda','evidencia':f"val_loss {best['val_loss']:.5f}→{last['val_loss']:.5f}; seeds proximas",'hipotese':'Regularizacao pode ajudar mais que aumentar capacidade','experimento':'Na Etapa 4, comparar arquitetura menor e regularizacao L2/dropout, mantendo protocolo e preprocessador','metrica':'Macro F1, BCE, gap treino-validacao, variacao entre sementes e custo','impacto_limitacoes':'Pode reduzir sobreajuste; drift e ambiguidade tambem limitam o ganho'},
      {'prioridade':4,'problema':'Calibracao e erros confiantes nao uniformes','evidencia':f"ECE10={s['ece_10']:.4f}; 879 erros com confianca≥0.9, 865 FN",'hipotese':'Recalibracao pode melhorar probabilidades, nao necessariamente discriminacao','experimento':'Calibracao em particao dedicada de desenvolvimento e protocolo de threshold com custos explicitados','metrica':'Brier, log loss, ECE com 10/20 bins, confiabilidade por grupo; precision/recall','impacto_limitacoes':'Nao usar os mesmos dados para calibrar, escolher limiar e estimar desempenho; nao abrir 2025'},
      {'prioridade':5,'problema':'Contribuicao temporal pequena e drift contextual','evidencia':'Permutacao: mes proximo de zero; dia pequeno; bairro/local dominam','hipotese':'Representacao temporal pode ser redundante ou fraca neste dominio','experimento':'Ablacao mes/dia ou codificacao ciclica em dobras temporais; manter periodo_fato excluido','metrica':'Macro F1, balanced accuracy, recall mensal e dispersao entre dobras','impacto_limitacoes':'Ausencia de importancia marginal nao prova inutilidade; dependencias podem esconder contribuicao'},
      {'prioridade':6,'problema':'Inferencia aceita valores sem suporte de treino e grafias novas','evidencia':'VIA PUBLICA sem acento vira ausente; mes/dia None ativam colunas nao observadas em 2023','hipotese':'Fallback silencioso pode produzir respostas tecnicamente validas fora do suporte','experimento':'Camada futura de validacao/avisos e aliases auditados; contrato explicito para ausencias temporais','metrica':'Testes de contrato, cobertura de fallback, taxa de entradas fora de suporte','impacto_limitacoes':'Melhora confiabilidade da interface; nao implica maior acuracia e nao altera o baseline nesta etapa'}]
    save('recomendacoes_etapa4',recommendation)
    recdoc='# Recomendações priorizadas para a Etapa 4\n\nNenhum experimento abaixo foi iniciado. Manter 2025 fechado; os diagnósticos de 2024 já foram consultados extensivamente, portanto não representam uma nova avaliação independente. Definir dobras temporais de desenvolvimento, critérios e orçamento antes de comparar modelos.\n\n'+table(recommendation)+'\n\nNão priorizar mais camadas sem evidência de insuficiência de capacidade. A estabilidade entre sementes é alta e há muitos contextos idênticos com duas classes. Não inferir segurança ou risco criminal de bairros.\n'
    (ROOT/'docs/recomendacoes_etapa4.md').write_text(recdoc,encoding='utf-8')
    text=f'''# Etapa 3 — Diagnóstico técnico da primeira MLP

## A. Integridade e protocolo

Baseline carregado: **299 → 64 ReLU → 1 sigmoid; 19.265 parâmetros**. Pré-processador original congelado: mês, dia da semana, tipo de local e bairro; nenhum período, natureza ou identificador como entrada. Threshold permanece **0,5**. Foram usados somente 190.124 BOs de 2023 e 158.895 de 2024. As novas análises não carregam 2025 para predição nem usam sua distribuição para decisões. Os testes legados consultam metadados/hashes para integridade e disjunção, sem avaliação preditiva desse ano.

{originals} arquivos anteriores conferidos por SHA256, sem alterações, incluindo modelo, pré-processador, datasets, scripts e relatórios. Alinhamento de 2023/2024 conferido por chave/índice e valores contra a base analítica. A matriz e as probabilidades de 2024 foram reproduzidas com tolerância 1e-7; qualquer divergência interrompe o diagnóstico. Não há novo ajuste do pré-processador. Evidências e tabelas completas em `etapa3/`.

## B. Análise dos erros

ROUBO é a classe positiva: **TN=68.328; FP=23.727; FN=25.962; TP=40.878**. São **49.689 erros**, exatamente os da Etapa 2. Taxa de falsos positivos entre furtos: **{100*m['fp']/m['furtos']:.2f}%**; taxa de falsos negativos entre roubos: **{100*m['fn']/m['roubos']:.2f}%**. Estes denominadores são as classes verdadeiras, não o total de erros.

![Erros por classe](etapa3/figures/erros_por_classe.png)

`metricas_grupos.csv` detalha FP/FN, suportes, taxas por classe, média das probabilidades de FP/FN e Wilson 95% para taxa de erro por mês, dia, local, bairro, raridade e ausências. Destaque exige n≥200 e pelo menos 30 casos de cada classe; balanced accuracy fica indisponível se falta uma classe. Macro F1 usa sempre os dois rótulos, com divisões indefinidas explicitadas como zero. Categorias de bairro pequenas não são destacadas nem publicadas individualmente na tabela de desempenho. Intervalos são descritivos, não corrigem comparações múltiplas ou dependências residuais entre BOs.

A via pública reúne 44.884 erros (90,33% de todos os erros), mas também concentra grande parte do volume e uma mistura mais equilibrada de classes. A taxa de erro de 35,96% deve ser lida junto ao suporte, e não como indicador de segurança. Em `tipo_local` ausente, a rede prevê FURTO para todos os 4.653 registros e perde os 479 roubos desse grupo. Alta acurácia nesse grupo não representa capacidade de reconhecer as duas classes.

Condições de bairro (aprendidas no treino, sem novos agrupamentos):

{table(conditions,['categoria','n','furtos','roubos','accuracy','macro_f1','balanced_accuracy','recall_roubo','fpr','fnr'])}

O bucket inclui **12.673 raros conhecidos + 355 novos = 13.028** BOs de validação. Em 2023 foram 14.244 raros, 247 bairros retidos e 1.913 nomes normalizados conhecidos. Há **247 nomes novos em 355 BOs de 2024**; não confundir quantidade de nomes com quantidade de registros. Os raros têm recall de roubo elevado, mas FPR muito maior que nos frequentes: o compartilhamento da representação pode favorecer uma classe e prejudicar outra. Essa comparação é observacional e as prevalências são diferentes; não prova que outro encoding melhoraria o resultado. O grupo novo tem suporte limitado e não autoriza conclusões sobre cada bairro. Nenhuma tabela constitui ranking de risco criminal.

## C. Generalização temporal, overfitting e underfitting

Histórico original: na época 5, loss={best['loss']:.5f}, val_loss={best['val_loss']:.5f}; na época 10, loss={last['loss']:.5f}, val_loss={last['val_loss']:.5f}. A queda de treino acompanhada da piora sustentada de validação após a melhor época é **compatível com sobreajuste incremental**; os melhores pesos já foram restaurados. O gap de acurácia dos pesos salvos é 70,15%−68,73%=1,42 ponto percentual. Esse gap isolado não identifica a causa; drift entre anos também pode contribuir. Curvas originais preservadas em `figures/curvas_mlp_baseline.png`.

Roubos passam de 44,03% no treino para 42,07% na validação. A distância de variação total entre distribuições categóricas é definida como metade da soma das diferenças absolutas de proporções, sobre a união dos níveis normalizados. É descritiva; não é teste de hipótese nem atribui causa.

{table(rows('drift_atributos'))}

Ausência de tipo de local por ano e classe:

{table(localmissing)}

A ausência cai de 7,38% para 2,93% no total, mas permanece fortemente ligada ao rótulo dentro de cada ano. `OUTROS` sobe de **12/190.124 (0,0063%)** para **7.706/158.895 (4,85%)**, enquanto a ausência cai 4,45 pontos percentuais. Isso sugere investigar recodificação/preenchimento; **não prova que os mesmos registros migraram de categoria nem identifica um procedimento administrativo específico**. Não foram examinados identificadores de delegacia para tentar confirmar causalidade. A ausência pode refletir características do fato e do relato, além da coleta. O atributo não foi excluído nem declarado vazamento confirmado.

Todas as categorias de tipo de local de 2024 já eram conhecidas; a mudança principal é de frequências, não de vocabulário. Bairros novos atingem somente 355 registros, mas há mudança mais ampla de composição de bairros já conhecidos. Relações categoria/rótulo por ano estão em `relacoes_categoria_rotulo.csv`, e distribuições em `distribuicoes_anos.csv`.

![Desempenho mensal](etapa3/figures/desempenho_temporal.png)

{table(temporal,['categoria','n','accuracy','macro_f1','balanced_accuracy','recall_roubo'])}

Acurácia mensal varia de {100*min(float(r['accuracy']) for r in temporal):.2f}% a {100*max(float(r['accuracy']) for r in temporal):.2f}%; recall de roubo de {100*min(float(r['recall_roubo']) for r in temporal):.2f}% a {100*max(float(r['recall_roubo']) for r in temporal):.2f}%. Não há deterioração monotônica; composição e prevalência variam. Trimestres e suportes constam na tabela completa. A rede não prevê a evolução do crime.

Ambiguidade dos atributos codificados:

{table(rows('ambiguidade_contextos'))}

O “teto empírico” soma a classe mais frequente em cada tupla **do próprio conjunto**, sem treinar outro modelo. É um limite retrospectivo da acurácia determinística nesta amostra e representação, **não um limite Bayesiano populacional nem desempenho atingível em dados futuros**. Muitos contextos idênticos têm ambas as classes, inclusive antes de codificar. Não há evidência suficiente para diagnosticar underfitting de capacidade ou justificar simplesmente mais camadas.

## D. Influência aparente dos atributos

Permutação agrupada por campo original: amostra aleatória simples fixa de 30.000 BOs de 2024 (semente 314159), cinco embaralhamentos por campo, métricas comparadas ao baseline **na mesma amostra**. O pré-processador permanece congelado e cada permutação mantém uma categoria válida por atributo; não embaralha dummies independentes.

{table(imp)}

![Importância marginal](etapa3/figures/importancia_atributos.png)

Bairro tem a maior queda média de Macro F1 (~11,66 pontos percentuais), seguido de local (~6,47). Dia contribui pouco (~0,22) e mês fica próximo de zero (~0,01), dentro da variação das permutações. Não é evidência de que mês seja inútil em qualquer contexto. A permutação marginal quebra dependências e cria combinações bairro/local/tempo pouco plausíveis; pode distorcer a importância quando atributos são correlacionados. O DP de cinco permutações mede instabilidade do embaralhamento, não intervalo de confiança populacional. Importância preditiva não é causalidade e pesos da rede não foram usados como importância direta.

## E. Probabilidades, confiança e limiares

**Brier={s['brier']:.6f}; Log Loss={s['log_loss']:.6f}; ECE10={s['ece_10']:.6f}; ECE20={s['ece_20']:.6f}.** Brier da previsão constante com prevalência de treino: {s['brier_constante_prevalencia_treino']:.6f}. Brier é a média de (p−y)²; Log Loss penaliza probabilidades erradas com confiança alta. Ambas combinam discriminação e confiabilidade, portanto menor valor não prova melhor calibração isoladamente.

ECE é Σ(n_bin/N)·|média(p_bin)−frequência(ROUBO_bin)|, com 10 ou 20 intervalos de mesma largura em [0,1], fechados à esquerda e abertos à direita; o último inclui 1. Intervalos vazios não contribuem. `calibracao_bins.csv` registra limites e suportes. ECE depende da escolha dos intervalos e pode esconder erros de subgrupos. Nenhum calibrador foi ajustado.

P(ROUBO) média={s['prob_roubo_media']:.4f}, frequência observada={s['prevalencia_roubo']:.4f}. Há leve superestimação média, sem evidência aqui de descalibração global extrema; a qualidade local não está garantida. Confiança é max(p,1−p); probabilidade da classe verdadeira usa p nos roubos e 1−p nos furtos.

{table(conf)}

Os erros têm confiança média **65,18%**; há **879 erros com confiança ≥90%**, dos quais **865 são falsos negativos**. Não interpretar os 879 como 879/49.689 de erro nos casos confiantes: entre todas as 13.105 previsões com confiança ≥90%, 879 erram (6,71%). Há erros individuais confiantes relevantes mesmo com ECE global moderado.

![Distribuições](etapa3/figures/distribuicao_confianca.png)
![Confiabilidade](etapa3/figures/curva_calibracao.png)
![Limiares diagnósticos](etapa3/figures/precision_recall_limiares.png)

Foram calculados precision, recall, F1 e quantidade de previsões de roubo para limiares 0,05–0,95, em passos de 0,05. A curva mostra o compromisso entre recuperar roubos e aumentar falsos positivos. **Nenhum limiar foi selecionado ou substituído; o operacional continua 0,5.** Usar o mesmo 2024 para explorar, calibrar, escolher limiar e reportar um ganho final produziria estimativa otimista; a próxima etapa precisa de protocolo de desenvolvimento separado.

## F. Robustez da interface

Contrato confirmado: mês inteiro 1–12; dia inteiro 0–6 (segunda=0); ambos aceitam None. Local/bairro devem ser texto ou None. Strings numéricas de mês, floats, booleanos, NaN/inf, categorias numéricas e domínios inválidos são rejeitados previsivelmente. Entradas extras, inclusive período, alvo e chave, são recusadas pelo pré-processador. As probabilidades são finitas, estão em [0,1], somam 1 e seguem o limiar. Inferência recarrega os artefatos sem depender dos datasets.

Caixa, espaços e Unicode decomposto são normalizados. BRÁS/BRAS são equivalentes por alias explícito. Entretanto, **VIA PUBLICA sem acento não é igual a VIA PÚBLICA** no contrato atual: vira local desconhecido e usa a categoria ausente, com mudança possível de previsão. Isso é comportamento do baseline preservado, não correção aplicada. Tipos de local novos compartilham o fallback enviesado para FURTO observado na validação. Bairros novos compartilham o bucket raro. O texto de bairro `152` vira ausente silenciosamente, enquanto o número 152 é rejeitado: recomendar aviso/validação explícita em evolução futura da interface.

Outro limite: as categorias de ausência de mês/dia existem no encoder, mas **não foram observadas no treino**. A interface produz resposta finita para None, mas isso não valida cientificamente a resposta fora do suporte; os pesos dessas colunas não foram aprendidos com exemplos. Não alterar o baseline para corrigir esses pontos nesta etapa. Sondagens sintéticas, sem registros reais individuais, em `sondagens_inferencia.csv`.

## G. Estabilidade de treinamento

Três execuções adicionais foram concluídas, sem seleção de vencedor: controle com semente 42 e sementes 7/123. Mesma arquitetura, hiperparâmetros, pré-processador original e conjuntos completos. A ordem dos lotes usa RNG 42 em todas, reproduzindo o código original; varia a semente global da inicialização. PYTHONHASHSEED=42, determinismo TensorFlow habilitado, CPU e threads iguais, oneDNN desabilitado. Cada execução ocorre em processo separado.

{table([{k:r[k] for k in ['seed','epochs','best_epoch','seconds','accuracy','macro_f1','balanced_accuracy','recall_roubo']} for r in stability])}

{table([{'metrica':k,**v} for k,v in read('estabilidade_resumo.json').items()])}

Controle 42: diferença máxima de probabilidade em relação ao baseline={stability[0]['baseline_max_abs_diff']:.10f}; reprodução dentro de 1e-7={stability[0]['baseline_reproduced_atol_1e7']}. A acurácia varia aproximadamente 68,694%–68,737%, com DP amostral de 0,023 ponto percentual. Essa pequena amostra sugere baixa sensibilidade à inicialização neste protocolo, mas não garante estabilidade em outra máquina, divisão ou conjunto. Não é busca de hiperparâmetros. Checkpoints em `models/experimentos_etapa3/`; baseline original intacto.

## H. Testes, preservação e reprodução

{table(tests)}

**{ntests} testes efetivamente executados**, mantendo os 23 anteriores. Logs e falhas, se houver, em `etapa3/`. Os testes novos cobrem entradas adversas, caixa/acento, raros/novos/ausentes, probabilidades, determinismo de inferência, independência dos datasets, não mutação do pré-processador, hashes, matriz reproduzida, protocolo de sementes e bloqueio de 2025. Os testes estruturais não provam ausência absoluta de proxies ou vazamento indireto.

Na primeira passagem, grupos com uma única classe emitiram avisos de métricas indefinidas. A rotina foi explicitada: matriz sempre 2×2, Macro F1 com dois rótulos e balanced accuracy ausente quando falta uma classe; os agregados foram regenerados. Nenhum artefato anterior foi alterado. Não foram expostos BOs, identificadores, endereços ou exemplos individuais reais.

Com ambiente da Etapa 2 e PYTHONPATH=src, PYTHONHASHSEED=42:

```powershell
python -m diagnostics.analyze
python -m diagnostics.repeat_runs
python -m diagnostics.run_tests
python -m diagnostics.report
```

As repetições são opcionais ao apenas rever o relatório existente; reexecutar o comando treina novamente somente os três checkpoints experimentais. Dependências existentes em `requirements-ml.txt`. Notebook executado: `notebooks/03_diagnostico_mlp.ipynb`; scripts: `src/diagnostics/`. As tabelas são agregadas; não há novas previsões individuais exportadas nem frontend/API/dashboard.

## I. Recomendações priorizadas para a Etapa 4

{table(recommendation)}

Documento separado: `docs/recomendacoes_etapa4.md`. Priorizar investigação do proxy de local, representação/contrato de bairros e validação temporal antes de aumentar capacidade. Comparar regularização/arquitetura menor com hipótese explícita; não presumir que mais neurônios superarão ambiguidade. Nenhum desses experimentos foi iniciado.

Referências metodológicas: [calibração — scikit-learn](https://github.com/scikit-learn/scikit-learn/blob/main/doc/modules/calibration.rst), [permutação — scikit-learn](https://scikit-learn.org/stable/modules/permutation_importance.html), [EarlyStopping — Keras](https://keras.io/api/callbacks/early_stopping/). Consulta em 09/11/2026. Métricas e conclusões empíricas acima são calculadas localmente sobre os artefatos do projeto.

O diagnóstico se restringe a BOs elegíveis de **celulares subtraídos da capital**, não a todos os crimes e não a risco futuro. **2025 permanece fechado e o desenvolvimento termina na Etapa 3.**
'''
    (ROOT/'reports/relatorio_etapa3.md').write_text(text,encoding='utf-8')
    notebook();preserve();print(text,flush=True)

def notebook():
    cells=[]
    def md(s):cells.append({'cell_type':'markdown','metadata':{},'source':s.splitlines(keepends=True)})
    def code(s):cells.append({'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':s.splitlines(keepends=True)})
    md('# Etapa 3 — Diagnóstico e robustez da primeira MLP\n\nModelo congelado para BOs envolvendo celulares subtraídos da capital. 0=FURTO, 1=ROUBO. Não prevê crimes futuros. Somente 2023/2024; 2025 permanece sem avaliação. O notebook lê agregados dos scripts reproduzíveis, sem repetir treinos automaticamente.')
    code("from pathlib import Path\nimport json,csv\nROOT=Path.cwd()\nif not (ROOT/'reports').exists():ROOT=ROOT.parent\nOUT=ROOT/'reports/etapa3'\ndef show(name,attribute=None):\n    with (OUT/(name+'.csv')).open(encoding='utf-8-sig') as f:\n        for row in csv.DictReader(f):\n            if attribute is None or row.get('atributo')==attribute:print(row)\nprint(json.loads((OUT/'resumo.json').read_text(encoding='utf-8')))\n")
    md('## Erros e condições de bairro\n\nMatriz reproduzida: TN=68.328, FP=23.727, FN=25.962, TP=40.878. Destaques exigem n≥200 e pelo menos 30 exemplos por classe. Taxas altas com prevalências diferentes não são diretamente comparáveis. Bairros não são classificados em níveis de segurança.')
    code("show('metricas_grupos','condicao_bairro')\nshow('metricas_grupos','presenca_local')\n")
    md('![Erros por classe](../reports/etapa3/figures/erros_por_classe.png)\n\n## Generalização\n\nA ausência de local se associa ao rótulo em ambos os anos; OUTROS muda de 12 para 7.706 registros. Isso é sinal para investigar preenchimento ou recodificação, não prova de vazamento. A piora de val_loss após a época 5 é compatível com sobreajuste incremental, mas o drift também contribui ao gap. Não há evidência suficiente para concluir underfitting por capacidade.')
    code("show('ausencias_ano_classe','tipo_local')\nshow('drift_atributos')\nshow('ambiguidade_contextos')\n")
    md('![Métricas por mês](../reports/etapa3/figures/desempenho_temporal.png)\n\n## Influência preditiva\n\nPermutação de atributos originais, amostra fixa de 30 mil BOs de 2024, cinco repetições. Bairro e local dominam. Importância marginal quebra dependências e não mede causalidade; DP não é IC populacional. Nenhum atributo foi removido.')
    code("show('importancia_atributos')\n")
    md('![Importância](../reports/etapa3/figures/importancia_atributos.png)\n\n## Probabilidades\n\nBrier e Log Loss combinam discriminação e confiabilidade. ECE usa 10 e 20 bins de largura uniforme, com último incluindo 1. ECE global pode esconder problemas de subgrupos. Não foi ajustado calibrador, e o threshold permanece 0,5.')
    code("show('confianca')\n")
    md('![Confiança](../reports/etapa3/figures/distribuicao_confianca.png)\n![Calibração](../reports/etapa3/figures/curva_calibracao.png)\n![Limiares](../reports/etapa3/figures/precision_recall_limiares.png)\n\n## Robustez e estabilidade\n\nCaixa/espaços e aliases de bairro são consistentes, mas local sem acento pode cair no fallback de ausente. Mês/dia None não tiveram exemplos de treino. Essas limitações foram documentadas sem modificar o baseline. Controle 42 e duas sementes adicionais mantêm arquitetura, hiperparâmetros e pré-processador. Nenhum vencedor foi escolhido.')
    code("show('estabilidade_sementes')\nshow('sondagens_inferencia')\nprint((OUT/'testes.json').read_text(encoding='utf-8'))\n")
    md('## Recomendações e limites\n\nPriorizar ablação controlada de tipo de local, raridade de bairros, validação temporal e contrato da inferência. Comparar regularização com hipótese de sobreajuste, sem presumir ganhos por aumentar camadas. Reservar dados próprios para calibração/threshold; os mesmos dados não podem avaliar imparcialmente a escolha. Ver `../docs/recomendacoes_etapa4.md` e `../reports/relatorio_etapa3.md`. Nenhuma Etapa 4 foi iniciada.')
    ns={};count=0
    for c in cells:
        c['id']=uuid.uuid5(uuid.NAMESPACE_URL,''.join(c['source'])).hex[:12]
        if c['cell_type']=='code':
            count+=1;buf=io.StringIO()
            with contextlib.redirect_stdout(buf):exec(''.join(c['source']),ns)
            c['execution_count']=count;c['outputs']=[{'output_type':'stream','name':'stdout','text':buf.getvalue().splitlines(keepends=True)}]
    nb={'cells':cells,'metadata':{'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},'language_info':{'name':'python','version':'3.12.14'}},'nbformat':4,'nbformat_minor':5}
    (ROOT/'notebooks/03_diagnostico_mlp.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1),encoding='utf-8')

if __name__=='__main__':generate()
