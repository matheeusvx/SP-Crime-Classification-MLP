"""Relatorio final e notebook a partir do unico resultado salvo, sem nova inferencia2025."""
from final5.common import *
from final5.metrics import calibration_bins
import numpy as np,io,contextlib,uuid
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from zoneinfo import ZoneInfo

def rows(name):
    with (OUT/(name+'.csv')).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def table(rs,cols=None):
    if not rs:return '(sem linhas)'
    cols=cols or list(rs[0]);fmt=lambda v:f'{v:.6f}' if isinstance(v,float) else str(v)
    return '| '+' | '.join(cols)+' |\n| '+' | '.join(['---']*len(cols))+' |\n'+'\n'.join('| '+' | '.join(fmt(r.get(c,'')) for c in cols)+' |' for r in rs)

def figures():
    m=read('metricas_2025.json');reference=read('referencia_majoritaria_2025.json')['metrics']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(11,5),layout='constrained')
    for ax,label,metric in [(axes[0],'Dense64 final',m),(axes[1],'Majoritário definido em 2023',reference)]:
        cm=np.asarray(metric['confusion_matrix']);ax.imshow(cm,cmap='Blues',vmin=0,vmax=99607)
        for i in range(2):
            for j in range(2):ax.text(j,i,f'{cm[i,j]:,}'.replace(',','.'),ha='center',va='center',fontsize=15)
        ax.set_xticks([0,1],['FURTO','ROUBO']);ax.set_yticks([0,1],['FURTO','ROUBO']);ax.set_xlabel('Classe estimada');ax.set_ylabel('Classe verdadeira');ax.set_title(label)
    fig.suptitle('Teste final independente · 2025 · Pipeline congelado, limiar 0,5');fig.savefig(OUT/'matriz_confusao_2025.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained');x=np.arange(2)
    for j,(key,label) in enumerate([('precision','Precision'),('recall','Recall'),('f1','F1')]):
        ax.bar(x+(j-1)*.24,[m[key+'_furto'],m[key+'_roubo']],width=.24,label=label)
    ax.set_xticks(x,['FURTO · n=99.607','ROUBO · n=56.561']);ax.set_ylim(0,1);ax.legend();ax.set_title('Desempenho por classe · Teste 2025')
    fig.savefig(OUT/'desempenho_por_classe.png',dpi=150);plt.close(fig)
    saved=np.load(OUT/'private/previsoes_2025.npz');p=saved['prob'];y=saved['y_true']
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for year in [2024,2025]:
        if year==2024:s=np.load(OUT/'private/validacao_2024.npz');bins=calibration_bins(s['y_true'],s['prob'])
        else:bins=calibration_bins(y,p)
        bins=[r for r in bins if r['n']>=200]
        axes[0].plot([r['prob_mean'] for r in bins],[r['roubo_frequency'] for r in bins],'o-',label=str(year)+' · bins n≥200')
    axes[0].plot([0,1],[0,1],'--',color='gray');axes[0].set_xlabel('P(ROUBO) estimada média');axes[0].set_ylabel('Frequência observada de ROUBO');axes[0].legend()
    for label in [0,1]:axes[1].hist(p[y==label],bins=np.linspace(0,1,21),histtype='step',lw=2,label='FURTO verdadeiro' if label==0 else 'ROUBO verdadeiro')
    axes[1].set_xlabel('P(ROUBO) estimada');axes[1].set_ylabel('Boletins');axes[1].legend()
    fig.suptitle('Probabilidades não calibradas · Diagnóstico final, sem ajustes posteriores');fig.savefig(OUT/'avaliacao_probabilidades.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,5),layout='constrained')
    for kind,label in [('sigmoid_original','Original'),('platt_candidato','Platt avaliado e rejeitado')]:
        rs=[r for r in rows('curva_calibracao_H2') if r['versao']==kind and int(r['n'])>=200]
        ax.plot([float(r['prob_mean']) for r in rs],[float(r['roubo_frequency']) for r in rs],'o-',label=label)
    ax.plot([0,1],[0,1],'--',color='gray');ax.set_xlabel('P(ROUBO) média');ax.set_ylabel('Frequência observada');ax.legend();ax.set_title('Holdout do calibrador Jul–Dez/2024 · Bins n≥200')
    fig.savefig(OUT/'calibracao_desenvolvimento_2024.png',dpi=150);plt.close(fig)
    months=sorted([r for r in rows('metricas_grupos_2025') if r['grupo']=='mes'],key=lambda r:int(r['categoria']))
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained');x=[int(r['categoria']) for r in months]
    for key,label in [('macro_f1','Macro F1'),('balanced_accuracy','Balanced accuracy'),('recall_roubo','Recall ROUBO')]:axes[0].plot(x,[float(r[key]) for r in months],'o-',label=label)
    axes[0].set_ylim(.5,.8);axes[0].set_xticks(x);axes[0].legend();axes[0].set_xlabel('Mês do fato · 2025')
    axes[1].bar(x,[int(r['n']) for r in months],color='#126C8A');axes[1].set_xticks(x);axes[1].set_xlabel('Mês do fato · 2025');axes[1].set_ylabel('Boletins')
    fig.suptitle('Diagnóstico mensal após o teste · Sem otimização');fig.savefig(OUT/'desempenho_mensal_2025.png',dpi=150);plt.close(fig)

def generate():
    preserve();manifest=verify_manifest();state=read('avaliacao_unica.json')
    if state['status']!='completed':raise RuntimeError('Teste final nao concluido')
    for p,h in state['result_hashes'].items():
        if sha256(ROOT/p)!=h:raise RuntimeError('Resultado final alterado: '+p)
    figures();m=read('metricas_2025.json');v=read('metricas_2024_pipeline_final.json');ref=read('referencia_majoritaria_2025.json');ci=read('intervalos_confianca_2025.json');d=read('decisao_calibracao.json')
    before=read('testes_previos.json');after=read('testes_posteriores.json');tests=before['suites']+after['suites'];ntests=sum(r['executados'] for r in tests)
    if not before['passed'] or not after['passed']:raise RuntimeError('Testes nao aprovados')
    saved=np.load(OUT/'private/previsoes_2025.npz');p=saved['prob'].astype(np.float64);y=saved['y_true'];pred=p>=.5;err=pred!=y
    diagnostics={'prob_roubo_mean':float(p.mean()),'roubo_prevalence':float(y.mean()),'mean_confidence_errors':float(np.maximum(p[err],1-p[err]).mean()),
      'predicted_furtos':int(np.sum(~pred)),'predicted_roubos':int(np.sum(pred)),'n_errors':int(np.sum(err)),
      'high_conf_predictions':int(np.sum(np.maximum(p,1-p)>=.9))}
    json_write(OUT/'resumo_diagnostico.json',diagnostics)
    metrics_table=[{'metrica':k,'validacao_2024':v[k],'teste_2025':m[k],'diferenca_2025_menos_2024':m[k]-v[k]} for k in ['accuracy','precision_roubo','recall_roubo','f1_roubo','precision_furto','recall_furto','f1_furto','macro_f1','balanced_accuracy','brier','log_loss','ece10','ece20']]
    save('comparacao_metricas',metrics_table)
    class_rows=[{'classe':label,'suporte':m['furtos'] if key=='furto' else m['roubos'],'previsoes':diagnostics['predicted_furtos'] if key=='furto' else diagnostics['predicted_roubos'],**{metric:m[metric+'_'+key] for metric in ['precision','recall','f1']}} for key,label in [('furto','FURTO'),('roubo','ROUBO')]]
    save('metricas_por_classe_2025',class_rows)
    calrows=[r for r in rows('comparacao_calibracao_2024') if r['periodo']=='H2_2024']
    groups=rows('metricas_grupos_2025');neighborhood=[r for r in groups if r['grupo']=='condicao_bairro'];missing=[r for r in groups if r['grupo']=='presenca_local']
    monthly=sorted([r for r in groups if r['grupo']=='mes'],key=lambda r:int(r['categoria']))
    locals_top=sorted([r for r in groups if r['grupo']=='tipo_local' and r['destacar']=='True'],key=lambda r:int(r['fp'])+int(r['fn']),reverse=True)[:8]
    localtime=datetime.datetime.fromisoformat(manifest['frozen_at']).astimezone(ZoneInfo('America/Sao_Paulo')).isoformat()
    decision=f'''# Decisão do modelo final

Modelo selecionado pelo usuário antes do teste: **B64_full_s42 / Dense64**, versão **{MODEL_ID}**. Esta documentação consolida as decisões do manifesto, sem alterar os artefatos avaliados.

- Origem: `models/experiments/etapa4/B64_full_s42/`, modelo e pré-processador byte a byte idênticos às cópias em `models/final/`.
- Entradas: mês, dia da semana, tipo de local e bairro; 299 colunas One-Hot, Dense64 ReLU e sigmoid, 19.265 parâmetros. Adam0,001, BCE, batch256, três épocas, semente42. Sem dropout ou L2.
- Motivo: desempenho semelhante entre alternativas, estabilidade em três sementes e simplicidade relativa. Dense32 permanece alternativa compacta;64→32 teve maior recall e mais FP. Nenhuma alternativa foi comparada em2025.
- Pré-processador: o objeto experimental original, escopo completo2023, 190.124 registros, frequência mínima50 e alias unívoco de acentuação de local. Não há novo ajuste de vocabulário ou pesos.
- Calibração: **rejeitada antes do teste**. Platt melhorou Brier/Log Loss no holdout2024, mas recall de roubo caiu de {100*d['assessment_uncalibrated']['recall_roubo']:.2f}% para {100*d['assessment_calibrated']['recall_roubo']:.2f}%, além do limite de1pp previamente registrado. Não foi criado calibrador.joblib final. Threshold0,5 e sigmoid original mantidos.
- Congelamento: **{localtime}**, horário de São Paulo; registro UTC original em `models/final/manifesto.json`. SHA256 do manifesto: `{sha256(FINAL/'manifesto.json')}`.
- Inferência2025 iniciada somente em `{state['inference_started_at']}` UTC, após75 testes prévios. O registro de avaliação tem uma chamada de inferência em lotes e impede repetição silenciosa. Não houve ajuste após o teste.

Limitações: domínio de celulares subtraídos da capital; contexto ambíguo; possíveis efeitos administrativos; mudança de distribuição; saída não calibrada; ausência temporal sem exemplos no treino; bucket compartilhado entre raros e novos. Não determina juridicamente roubo/furto, não prevê crimes futuros, não é sistema oficial e não foi validado para decisões policiais/operacionais reais.
'''
    (ROOT/'docs/decisao_modelo_final.md').write_text(decision,encoding='utf-8')
    text=f'''# Etapa 5 — Seleção, congelamento e avaliação final da MLP

## A. Modelo selecionado

**{MODEL_ID}: Dense64, origem B64_full_s42.** Quatro entradas, na ordem `mes`, `dia_semana`, `tipo_local`, `bairro`; 299 colunas One-Hot; uma camada Dense64 ReLU e uma saída sigmoid; **19.265 parâmetros**. Adam0,001, BCE, batch256, três épocas, semente42 e ordem dos lotes42; sem dropout/L2. Frequência mínima50 para bairros, 247 frequentes retidos e equivalência unívoca de acentuação de local, `local_alias=True`.

A seleção foi definida pelo usuário antes de2025, com base na estabilidade em três sementes, desempenho semelhante das alternativas e ausência de ganho consistente de maior capacidade. Dense32 permanece alternativa compacta, e64→32 alternativa de maior recall com mais FP. Não houve novo treino nem seleção de semente nesta etapa. O baseline histórico e os experimentos anteriores foram preservados.

As regras são exatamente as do objeto experimental: NFC, espaços/maiúsculas, aliases de bairro ativos no treino, correspondência unívoca de acentuação de local, `OUTROS` separado de ausência, local novo representado como ausente e bairros raros/novos no bucket treinado. Não há natureza, rubrica, chave, ano, hora, período, indicador administrativo adicional ou informação pessoal nas entradas.

## B. Congelamento e integridade

Modelo e pré-processador originais foram conferidos pelos hashes experimentais e copiados sem mudanças para `models/final/`. Todas as158.895 probabilidades de2024 foram reproduzidas; diferença absoluta máxima={read('verificacao_previa_2024.json')['max_abs_difference']:.10f}. Macro F1 reproduzida={v['macro_f1']:.6f}, compatível com67,69% da Etapa4. Dimensões, ordem das299 colunas, rótulos e efeitos de aliases foram verificados.

Congelamento registrado em **{localtime}**, horário de São Paulo. Manifesto: `../models/final/manifesto.json`; SHA256=`{sha256(FINAL/'manifesto.json')}`. Modelo SHA256=`{manifest['frozen_files']['modelo.keras']}`; pré-processador SHA256=`{manifest['frozen_files']['preprocessador.joblib']}`. O manifesto registra arquitetura, hiperparâmetros, regras, categorias, rótulos, código necessário à inferência, versões, fonte, protocolo e limitações. Sidecar `manifesto.sha256` permite verificar sua integridade.

Os75 testes prévios foram aprovados antes de abrir2025 para inferência. A avaliação começou em `{state['started_at']}` UTC, com inferência em `{state['inference_started_at']}` UTC, depois do congelamento. Há **uma única chamada planejada de inferência em lotes**, sobre todos os156.168 registros. O registro `etapa5/avaliacao_unica.json` impede outra inferência silenciosa e valida hashes de resultados quando chamado novamente. Os testes posteriores usam apenas probabilidades salvas.

Arquivos das quatro etapas anteriores intactos por SHA256: **{preserve()}**. Dataset de teste conferido contra a definição da Etapa1 por chave/índice, alvo, data do fato e município3550308: zero divergências,156.168 chaves únicas e nenhuma chave em anos diferentes. Os hashes dos datasets processados são os registrados no experimento escolhido. Nenhuma transformação foi reajustada em2025.

## C. Decisão de calibração — tomada antes do teste

Protocolo e limites quantitativos foram registrados em `etapa5/protocolo_previo.json` antes do ajuste. Uma única regressão logística de Platt sobre logit da sigmoid, clip1e-7, C=1e6, lbfgs, max_iter1000, tol1e-10, random_state42. Ajuste em **80.321 registros Jan–Jun/2024** e verificação em **78.574 Jul–Dez/2024**. A rede não mudou. Não houve busca de thresholds nem segundo método.

Para adotar: reduzir Brier≥0,001 e Log Loss≥0,002; ECE10/20 não piorar mais que0,002; Macro F1 perder no máximo0,005; recall perder no máximo0,01; inclinação positiva e ausência de piora probabilística relevante em Q3/Q4. Todos os critérios eram necessários.

{table(calrows,['versao','n','brier','log_loss','ece10','macro_f1','recall_roubo'])}

**Calibração rejeitada.** O ganho probabilístico foi consistente pelos limites definidos, mas o recall caiu **{100*(d['assessment_uncalibrated']['recall_roubo']-d['assessment_calibrated']['recall_roubo']):.2f} pp**, excedendo1pp. Houve2.508 mudanças de classificação em H2 com threshold0,5. A decisão manteve a sigmoid original e não foi criado `calibrador.joblib` final. Os coeficientes candidatos constam do diagnóstico, não participam da inferência final. Não foi calculado resultado calibrado de2025 para reconsiderar a decisão.

![Calibração em desenvolvimento](etapa5/calibracao_desenvolvimento_2024.png)

2024 já havia participado da escolha de arquiteturas e diagnósticos. H2 é holdout do calibrador, mas não é independente de todas as decisões do projeto; a avaliação independente permaneceu2025.

## D. Resultado final independente — 2025

Distribuição real: **{m['furtos']:,} FURTOS ({100*m['furtos']/m['n']:.2f}%)** e **{m['roubos']:,} ROUBOS ({100*m['roubos']/m['n']:.2f}%)**, total **{m['n']:,}**. Classe positiva=ROUBO.

{table([{'metrica':r['metrica'],'resultado_2025':r['teste_2025']} for r in metrics_table])}

{table(class_rows)}

**Matriz: TN={m['tn']:,}; FP={m['fp']:,}; FN={m['fn']:,}; TP={m['tp']:,}.** As linhas são classes verdadeiras e colunas previstas, na ordem FURTO, ROUBO. Total de erros={m['fp']+m['fn']:,}; FPR entre furtos={100*m['fp']/m['furtos']:.2f}%; FNR entre roubos={100*m['fn']/m['roubos']:.2f}%.

![Matriz final e referência](etapa5/matriz_confusao_2025.png)
![Métricas por classe](etapa5/desempenho_por_classe.png)

Referência majoritária compatível: classe FURTO definida no treino2023 (106.421 furtos contra83.703 roubos), sem consultar o teste para escolher a classe. Probabilidade constante de roubo=83.703/190.124, também do treino, usada apenas para métricas probabilísticas da referência. No teste: accuracy={ref['metrics']['accuracy']:.6f}; Macro F1={ref['metrics']['macro_f1']:.6f}; balanced accuracy=0,5 e recall roubo=0. A Dense64 supera a referência em **{100*(m['accuracy']-ref['metrics']['accuracy']):.2f} pp de acurácia** e **{100*(m['macro_f1']-ref['metrics']['macro_f1']):.2f} pp de Macro F1**, sem confundir acurácia com desempenho equilibrado.

IC95% das métricas principais:

{table([{'metrica':k,**r} for k,r in ci['metrics'].items()])}

10.000 réplicas IID não paramétricas da distribuição conjunta das quatro células(y,pred), via multinomial, seed12345, percentis2,5 e97,5. Para métricas de matriz fixa, equivale a reamostrar BOs. Intervalos condicionais ao pipeline, sem variabilidade de treinamento/seleção e sem corrigir dependências residuais ou mudança temporal; não são garantia de desempenho em outra população.

## E. Generalização: 2024 versus 2025

{table(metrics_table)}

A prevalência de roubo caiu de **{100*v['roubos']/v['n']:.2f}%** para **{100*m['roubos']/m['n']:.2f}%**. A acurácia subiu {100*(m['accuracy']-v['accuracy']):+.2f} pp, mas Macro F1 mudou {100*(m['macro_f1']-v['macro_f1']):+.2f} pp, balanced accuracy {100*(m['balanced_accuracy']-v['balanced_accuracy']):+.2f} pp e recall roubo {100*(m['recall_roubo']-v['recall_roubo']):+.2f} pp. A precision de roubo caiu {100*(m['precision_roubo']-v['precision_roubo']):.2f} pp. A queda de prevalência e a mudança de contexto são hipóteses consistentes com essa combinação, não causas demonstradas.

**A confiabilidade probabilística piorou:** ECE10 passou de {100*v['ece10']:.2f}% para **{100*m['ece10']:.2f}%**. P(ROUBO) média={diagnostics['prob_roubo_mean']:.4f}, acima da frequência real={diagnostics['roubo_prevalence']:.4f}. Brier/Log Loss ficaram ligeiramente menores, mas essas medidas combinam confiabilidade, discriminação e incerteza da população; sua redução não demonstra melhora de calibração. A mudança de prevalência altera sua interpretação. As probabilidades continuam estimadas e não calibradas; **nenhum ajuste foi feito após observar essa piora**.

![Probabilidades e confiabilidade](etapa5/avaliacao_probabilidades.png)

As curvas de confiabilidade exibem somente intervalos com pelo menos200 exemplos, evitando destacar taxas instáveis nas caudas. ECE10/20 e demais métricas incluem todos os registros e intervalos; suportes constam nas tabelas de bins. Essa restrição é apenas visual, sem alteração do pipeline ou dos resultados do teste.

Mudanças de distribuição normalizada:

{table(rows('mudanca_distribuicao_2024_2025'))}

Tipo de local ausente passou de4.653/158.895 (2,93%) para **68/156.168 (0,044%)**. Em2025 são34 furtos e34 roubos sem local, contra4.174 furtos e479 roubos em2024. É uma mudança expressiva de preenchimento; não foi usada para retocar o modelo e não prova recodificação específica. OUTROS contém11.901 registros em2025, acima dos7.706 de2024. Tipos de local novos em relação ao treino:0. Bairros desconhecidos do treino:389 registros, contra355 em2024; raros e novos continuam compartilhando representação. A tabela de drift compara níveis2024/2025, enquanto o contador desconhecido do pré-processador se refere a2023 — denominadores distintos.

## F. Análise dos erros finais — apenas diagnóstica

Há **{m['fp']:,} FP** e **{m['fn']:,} FN**. **{m['high_conf_errors']} erros têm confiança≥90%**, sendo **{m['high_conf_fn']} FN**. Confiança média dos erros={100*diagnostics['mean_confidence_errors']:.2f}%. As previsões estimam{diagnostics['predicted_roubos']:,} roubos, diante de{m['roubos']:,} verdadeiros. Confiança na classe prevista=max(p,1−p), diferente de p para roubo.

Locais com maior número absoluto de erros entre os de suporte suficiente:

{table(locals_top,['categoria','n','furtos','roubos','fp','fn','macro_f1','balanced_accuracy','recall_roubo','high_conf_errors'])}

Via pública concentra grande volume e sobreposição de classes; OUTROS e terminal/estação têm muitos roubos classificados como furtos. Isso descreve o classificador, não causalidade criminal. Grupos com pelo menos200 BOs e30 de cada classe são destacados; grupos menores, como local ausente(n=68), não sustentam conclusões gerais.

{table(neighborhood,['categoria','n','furtos','roubos','fp','fn','macro_f1','balanced_accuracy','recall_roubo'])}

Raros conhecidos:12.986; desconhecidos:389; frequentes:142.253; bairro ausente:540. O recall elevado nos buckets raros/novos acompanha muitos falsos positivos: não é desempenho equilibrado. Nenhum ranking individual de bairro ou indicador de segurança foi construído.

{table(missing,['categoria','n','fp','fn','macro_f1','recall_roubo','destacar'])}

Desempenho mensal e suporte:

{table(monthly,['categoria','n','accuracy','macro_f1','balanced_accuracy','recall_roubo'])}

![Diagnóstico mensal](etapa5/desempenho_mensal_2025.png)

As diferenças entre meses podem refletir composição e prevalência, sem identificar causa ou prever ocorrências futuras. Esses resultados não alteraram pesos, vocabulários, frequências, threshold, calibração ou escolha de arquitetura.

## G. Robustez e contrato de inferência

Interface: `from final5.pipeline import FinalPipeline`; carregar uma vez e chamar `classificar(mes,dia_semana,tipo_local,bairro)`. Retorna classe/código, probabilidades de furto/roubo, versão **{MODEL_ID}**, `probabilidades_calibradas=False` e avisos estruturados. A inferência funciona sem XLSX/Parquet ou rótulos. A mesma transformação do treinamento é usada, sem reimplementação.

Mês inteiro1–12, dia inteiro0–6 (segunda=0), texto/None para local e bairro. Tipos errados, booleanos, NaN/inf, valores fora de domínio e atributos extras são recusados. Caixa/espaços e variantes de acento permitidas são consistentes. Ausentes, raros e novos geram avisos. Mês/dia None ativam categorias sem exemplos de treino e produzem aviso específico. Bairro textual sem letras mantém a conversão original para ausente com aviso; número tipado é rejeitado. O objeto não aceita silenciosamente valores inválidos. Detalhes em `../docs/contrato_inferencia.md` e no contrato congelado `../models/final/contrato.json`.

Limites de uso: (1) registros históricos de celulares subtraídos; (2) somente São Paulo capital; (3) não prevê crime futuro; (4) não determina natureza jurídica; (5) contexto não separa perfeitamente todas as ocorrências; (6) possíveis efeitos administrativos; (7) sensibilidade à distribuição; (8) demonstração acadêmica sem validação para decisões policiais ou operacionais reais. Não é sistema oficial de segurança pública.

## H. Testes e rastreabilidade

{table(tests)}

**{ntests} testes efetivamente executados e aprovados**, zero falhas/erros:75 prévios (57 existentes+18 novos) e8 posteriores. Os posteriores recalculam métricas e intervalos a partir do arquivo privado salvo, verificam hashes/manifesto e testam o bloqueio de nova inferência. A chamada ao avaliador nesse teste retorna o cache sem passar pela rede: não é outra avaliação.

O registro final contém timestamps, hashes de modelo/preprocessador/manifesto/resultados/código de avaliação e métricas, seeds TensorFlow42 e bootstrap12345, versões e identificação do teste. As verificações de integridade confirmam uma inferência após o congelamento, sem treino ou ajustes em2025. Não houve falha técnica durante a avaliação final nem necessidade de repetição. Correção de implementação anterior à primeira tentativa: importação de Path para registrar o hash do código; nenhum resultado de2025 existia nesse momento.

## I. Artefatos finais e reprodução

- `models/final/modelo.keras` e `preprocessador.joblib`: cópias íntegras da Dense64 selecionada.
- `models/final/config_final.json`, `contrato.json`, `manifesto.json` e `manifesto.sha256`: configuração e congelamento.
- **Não há calibrador final**, pois o candidato foi rejeitado pelos critérios prévios.
- `src/final5/pipeline.py`: inferência reutilizável; `protocol.py`, `prepare.py`, `evaluate.py`, `metrics.py`, `run_tests.py` e `report.py`: processo reproduzível.
- `reports/etapa5/metricas_2025.json`, matriz, métricas por classe, IC, comparação temporal e diagnósticos agregados.
- `notebooks/GS_Classificacao_MLP_Completo.ipynb`: notebook executado, sem treino, seleção ou nova inferência2025.
- `docs/decisao_modelo_final.md`, `protocolo_teste_final.md`, `contrato_inferencia.md` e `recomendacoes_etapa6.md`.
- `requirements-final.txt`: dependências fixadas de inferência; o ambiente completo anterior permanece disponível.

Com ambiente ML e PYTHONPATH=src, o processo registrado foi:

```powershell
python -m final5.protocol
python -m final5.prepare
python -m final5.run_tests pre
python -m final5.evaluate
python -m final5.run_tests post
python -m final5.report
```

Agora `prepare` verifica o congelamento sem reajustar, e `evaluate` verifica o resultado existente sem reinferir. Não remover os registros de avaliação para obter nova tentativa. Relatórios/figuras podem ser regenerados do cache. Previsões individuais estão somente em `etapa5/private/`, ignoradas pelo Git, e não integram os materiais públicos. O notebook consome resultados já salvos.

## J. Integração futura — Etapa 6

Carregar uma instância do pipeline por processo, preservar os quatro campos e avisos, expor a versão/calibração efetiva e manter os hashes e dependências. Não duplicar One-Hot no frontend nem permitir ajuste do modelo pelo formulário. Exibir limitações e ausência de calibração; não traduzir as saídas em risco criminal. Tratar erros de validação como erro de entrada. Não conectar datasets históricos ao serviço de inferência.

O teste2025 está encerrado: sua piora de calibração e os problemas de subgrupos são limitações da versão avaliada, não autorização para retocá-la. Uma nova versão futura exige outro protocolo e avaliação. A Etapa6 será somente integração do pipeline congelado, após autorização. Nenhuma API HTTP, frontend ou dashboard foi criada.

Referência metodológica: [calibração — documentação oficial scikit-learn](https://scikit-learn.org/stable/modules/calibration.html). Brier/Log Loss não isolam calibração; a decisão e os resultados deste projeto foram calculados localmente, sem envio das bases a serviços externos.

**A Etapa5 termina com modelo selecionado, congelado e avaliado uma vez em2025. Nenhum parâmetro foi alterado após o teste.**
'''
    (ROOT/'reports/relatorio_etapa5.md').write_text(text,encoding='utf-8');notebook();verify_manifest();preserve();print(text,flush=True)

def notebook():
    """Navegação atual; a reprodução original permanece no histórico Git."""
    path = ROOT/'notebooks/GS_Classificacao_MLP_Completo.ipynb'
    print('Notebook acadêmico consolidado:', path)
    return path

if __name__=='__main__':generate()
