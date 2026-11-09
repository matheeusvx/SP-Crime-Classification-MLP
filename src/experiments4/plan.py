from experiments4.common import *

def configs():
    base={'features':FEATURES,'min_count':50,'local_alias':False,'units':[64],'dropout':0.,'l2':0.,'lr':.001}
    return {
      'A0':base|{'hypothesis':'Referencia baseline sob validacao interna','factor':'referencia'},
      'A1':base|{'features':[f for f in FEATURES if f!='tipo_local'],'hypothesis':'Dependencia de possivel proxy de local','factor':'retirar tipo_local'},
      'A2':base|{'features':[f for f in FEATURES if f!='bairro'],'hypothesis':'Dependencia de geografia categorica','factor':'retirar bairro'},
      'A3':base|{'features':[f for f in FEATURES if f!='mes'],'hypothesis':'Mes pode ter contribuicao pequena e extrapolacao dificil','factor':'retirar mes'},
      'A4_10':base|{'min_count':10,'hypothesis':'Menor agrupamento preserva heterogeneidade dos bairros','factor':'frequencia minima 10'},
      'A4_100':base|{'min_count':100,'hypothesis':'Agrupamento mais forte reduz cardinalidade e variancia','factor':'frequencia minima 100'},
      'A5':base|{'local_alias':True,'hypothesis':'Equivalencia exclusiva de acentuacao melhora contrato sem recodificar OUTROS','factor':'alias de acentuacao de local'}}

def create():
    OUT.mkdir(parents=True,exist_ok=True);preserve()
    matrix=[{'id':k,**v} for k,v in configs().items()]
    plan={'version':PLAN_VERSION,'blocks':matrix,'internal_train':'2023-01-01 a 2023-09-30','internal_validation':'2023-10-01 a 2023-12-31',
       'selection_metric':'macro_f1','representation_tolerance':.002,'representation_recall_tolerance':.02,
       'representation_tiebreak':'sem tipo_local, sem mes, menor dimension; somente dentro da tolerancia e recall',
       'architecture_units':[[32],[64],[64,32]],'optional_128_64':'nao executar: limitar orcamento e investigar regularizacao antes de capacidade maior',
       'regularization':[{'dropout':.1,'l2':0.},{'dropout':0.,'l2':.0001}],
       'learning_rate_condition':'0.0005 so se quatro oscilacoes consecutivas de val_loss acima de 0.01; caso contrario nao executar',
       'common':{'lr':.001,'batch_size':256,'max_epochs':30,'patience':5,'restore_best_weights':True,'threshold':.5,'seed':42,'batch_order_seed':42},
       'stability_seeds':[42,7,123],'stability_configurations':2,'candidate_rule':'Top 2 internos por Macro F1, recall e simplicidade; alternativa de arquitetura diferente se a ate 0.005 do primeiro',
       'refit_rule':'Epocas fixas = mediana arredondada das melhores epocas internas (3 sementes se disponiveis), sem Early Stopping em 2024',
       'refit_configurations':'A0 novo protocolo; A1 sensibilidade proxy; tres arquiteturas B; top 2 do C com tres sementes; deduplicar configuracoes identicas',
       'A5_reuse':'Se matrizes internas identicas a A0, reutilizar pesos A0 e avaliar contrato de inferencia; nao repetir treino redundante',
       'no_test_2025':True,'no_calibrator':True,'no_web':True}
    p=OUT/'matriz_planejada.json'
    if p.exists() and read('matriz_planejada.json')!=plan:raise ValueError('Matriz planejada existente diferente; nao sobrescrever')
    json_write(p,plan)
    text='''# Protocolo experimental da Etapa 4

Registrado antes dos treinamentos. Matriz completa: `reports/etapa4/matriz_planejada.json`.

## Separacao e integridade

Treino interno: janeiro–setembro/2023. Validacao interna: outubro–dezembro/2023. Chaves de BO indivisas e disjuntas. Transformadores, frequencias e aliases ativados aprendidos so no treino correspondente. Avaliacao posterior em 2024 somente apos congelar representacao, candidatos e orcamentos. 2025 bloqueado no carregador preditivo; testes antigos usam apenas hashes/metadados de integridade.

Mes/dia usam One-Hot nominal. O dominio do calendario (12 meses, 7 dias) e uma regra fixa, nao vocabulario aprendido na validacao. O Q4 contem meses sem exemplos no treino interno: seus dummies nao aprendem efeitos, limitacao da extrapolacao anual a documentar. A3 testa retirada do mes; nao interpretar eventual vantagem como inutilidade universal. Nomes/alias/frequencias de local/bairro sempre vem do treino.

## Matriz limitada

- A0: quatro atributos e limiar 50, Dense64.
- A1/A2/A3: remover apenas local/bairro/mes, respectivamente.
- A4_10/A4_100: manter atributos e alterar apenas frequencia minima do bairro; 50 e A0.
- A5: apenas equivalencia de acentuacao com correspondencia univoca a uma categoria observada no treino; OUTROS e ausente permanecem distintos. Se matriz codificada identica, reutilizar A0 e provar equivalencia, sem repetir ajuste.
- B: 32, 64, 64→32 na mesma representacao escolhida internamente. A rede 64 pode reutilizar o ajuste A correspondente. 128→64 nao sera executada para priorizar hipoteses de regularizacao e limitar a bateria.
- C: sobre a arquitetura escolhida internamente, testar separadamente dropout 0,1 e L2=0,0001. Learning rate 0,0005 somente se houver quatro oscilacoes consecutivas de val_loss superiores a 0,01; nao explorar por diferencas pequenas.
- Estabilidade: duas configuracoes candidatas, sementes globais 42/7/123, lotes sempre RNG42. Nao selecionar pela melhor semente.

Comum: BCE, ReLU, sigmoid, Adam 0,001, batch256, max30 epocas, EarlyStopping interno em val_loss, paciencia5, melhores pesos restaurados. Threshold0,5 em todas as comparacoes. L2 adiciona penalidade ao loss monitorado; BCE sem penalidade tambem e calculada separadamente.

## Decisoes predefinidas

Principal: Macro F1. Representacoes a ate 0,002 da melhor e recall a ate 0,02 da referencia de maior Macro F1 sao elegiveis; entre elas priorizar retirar local (menor dependencia do proxy), retirar mes e menor dimensao. Examinar subgrupos e registrar a decisao antes de B. A5 pode ser incorporado quando a equivalencia da matriz for comprovada, sem mudar previsoes nos dados existentes.

Arquitetura/regularizacao: Macro F1 com recall e menor capacidade para diferencas ate 0,002. Duas candidatas internas, alternativa com arquitetura diferente se dentro de 0,005. Reajuste completo de 2023 com epocas fixadas pela melhor epoca interna; para candidatas com 3 sementes usar a mediana, mesmo orcamento para todas as sementes no reajuste. Avaliar 2024 uma vez por configuracao/semente planejada, sem retocar parametros depois.

Reajustar A0, A1 (sensibilidade ao proxy), as tres arquiteturas B e as duas candidatas, deduplicando configuracoes identicas. Sementes adicionais completas somente para as duas candidatas. Comparar baseline historico separado: ele usou 2024 no EarlyStopping, diferenca metodologica que impede chamar pequenas diferencas de ganho comprovado.

Registrar hipoteses, fatores, falhas, hashes, caminhos, historicos, metricas por classe/grupo, tempos e configuracoes inferiores. Cache somente quando config, dados, escopo, epocas e integridade dos arquivos coincidem. Sem calibracao, busca exaustiva, modelo definitivo ou aplicacao web. Esta etapa nao abre o teste final.
'''
    doc=ROOT/'docs/protocolo_experimental_etapa4.md'
    if not doc.exists():doc.write_text(text,encoding='utf-8')
    print('Matriz experimental registrada antes de treinar.',flush=True)

if __name__=='__main__':create()
