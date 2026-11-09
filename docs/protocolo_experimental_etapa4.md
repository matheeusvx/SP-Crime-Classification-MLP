# Protocolo experimental da Etapa 4

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

## Revisao registrada antes do Bloco B

O desempate mecanico favoreceu A3 (sem mes), mas a revisao qualitativa exigida pelo usuario identificou ganho de apenas 0,00134 em Macro F1 e perda de 0,03879 em recall frente a A0. Para nao privilegiar ganho pequeno com perda substancial de recuperacao de roubos, escolheu-se A5 (mesmos quatro atributos/limiar50, equivalencia de acento de local comprovada). Este julgamento sobrepoe o desempate de simplicidade da matriz original; nao altera a matriz de tentativas nem cria novo treino. O JSON registra a escolha mecanica, a revisao e os valores. A0/A3 continuam reportados integralmente. A revisao ocorreu antes de comparar arquiteturas e antes de qualquer previsao de 2024 nesta etapa.
