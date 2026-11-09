# Protocolo do teste final — registrado antes da calibracao e de 2025

Modelo fixado pelo usuario: B64_full_s42, Dense64, semente42, tres epocas. Nao retreinar, escolher outra semente ou usar2025 para decidir qualquer parametro. Manter quatro atributos, preprocessador original correspondente, aliases de local, frequencia50 e threshold0,5.

Antes do teste: conferir hashes experimentais; copiar bytes para models/final; reproduzir todas as previsoes de2024 e suas metricas; verificar esquema e inferencia. Em seguida, decidir a calibracao somente em2024, congelar modelo/preprocessador/configuracao/calibrador selecionado/contrato/codigo e registrar manifesto e hashes. Executar os57 testes anteriores e os testes finais previos. Somente se aprovados, abrir2025 para uma unica inferencia planejada. O registro de inicio impede repeticoes silenciosas. Uma falha exige investigacao documentada; nao autoriza escolher resultado melhor.

## Criterios de calibracao predefinidos

Uma unica regressao logistica de Platt sobre logit da sigmoid, clip1e-7; C=1e6, lbfgs, max_iter1000, tol1e-10, random_state42. Ajuste Jan–Jun/2024, avaliacao Jul–Dez/2024. A rede nao muda. Adotar somente se TODOS forem atendidos no segundo semestre: reduzir Brier em pelo menos0,001 e Log Loss em0,002; ECE10 e ECE20 nao pioram mais que0,002; Macro F1 nao perde mais que0,005; recall de roubo nao perde mais que0,01; inclinacao positiva; em Q3 e Q4, Brier nao piora mais que0,0005 e Log Loss0,001. Nao buscar thresholds nem outro calibrador apos observar resultados. Se rejeitado, manter sigmoid original e nao criar calibrador.joblib em models/final. Se adotado, manter o calibrador ajustado em H1, sem reajustar usando H2.

2024 ja participou da selecao e exploracao de arquiteturas; essa analise e de desenvolvimento e nao uma avaliacao independente de todas as decisoes. A decisao e registrada antes de2025.

## Avaliacao final

156.168 BOs esperados de2025, por ano do fato. Revalidar alinhamento por chave/indice contra a base analitica, rotulos e municipio, sem alterar dados. Executar o pipeline congelado em lotes256. Referencia: classe majoritaria e prevalencia calculadas exclusivamente no treino2023. Calcular accuracy, precision/recall/F1 de ambas as classes, Macro F1, balanced accuracy, matriz, Brier, Log Loss e ECE10/20 (bins uniformes [0,1], ultimo inclui1). Diagnosticos por mes, tipo de local, bairros frequentes/raros/novos e ausencias; sem registros individuais publicos. Destaques de grupo: n>=200 e pelo menos30 exemplos de cada classe.

IC95% para accuracy, Macro F1, balanced accuracy e recall de roubo: 10.000 replicas IID nao parametricas da distribuicao conjunta das quatro celulas (y,pred), via multinomial, seed12345; percentis2,5/97,5. Para metricas dependentes so da matriz, e equivalente a reamostrar BOs. Intervalos condicionais ao pipeline congelado, sem incerteza de treinamento/selecoes e sem corrigir dependencia residual ou multiplicidade dos subgrupos. Nao afirmar causalidade ou previsao de crime futuro.

Salvar previsoes individuais apenas localmente em pasta privada ignorada pelo Git; testes posteriores recalculam resultados dessas previsoes, sem nova inferencia em2025. Notebook le resultados e nao treina nem reavalia. Encerrar na Etapa5, sem HTTP/frontend/dashboard.
