# Etapa 5.6 — Correções pós-auditoria independente

**Revisão:** pos-auditoria-1.0.0, 09/11/2026. **Contrato seguro:** 1.1.0. **Modelo preservado:** gs-celulares-sp-dense64-v1.0.0. Escopo: documentação, validação independente de entradas, regressão e rastreabilidade local. Nenhum treinamento, seleção de modelo, calibração ou nova inferência de 2025 foi executado.

## Leitura e classificação dos achados

O relatório `auditoria_claude.md` foi lido integralmente antes de qualquer edição. Foram examinados relatório/decisão/protocolo de calibração da Etapa 5, contrato JSON/documentado, manifesto, fontes congeladas, pré-processamento experimental, inferência baseline e testes. Não se tomou o resumo do pedido como substituto da auditoria.

- **Correções comprovadas:** defeitos do contrato de entrada, marcação de legado, lacuna de comparação e interpretação inadequada de calibração. Implementadas ou corrigidas por erratas.
- **Riscos metodológicos:** proxies administrativos, viés de seleção, cobertura temporal, normalização fragmentada e independência limitada de 2025. Documentados; alguns mitigados por seleção controlada e bloqueio de desconhecidos, sem modificar o estimador.
- **Hipóteses experimentais:** H1–H9 da auditoria permanecem futuras. Nenhuma foi implementada.

Os números da referência por frequências e diagnósticos novos abaixo são atribuídos à auditoria, sem recálculo nesta manutenção. Os resultados históricos não foram substituídos.

## Estado das oito correções

| # | Estado | Ação e evidência | Arquivos principais |
| --- | --- | --- | --- |
| 1 | Documentação corrigida | Comparação retrospectiva por frequências, AUC e conclusão conservadora. Não há ganho consistente demonstrado da rede além da maioria. | relatório Etapa 5, decisão final, README e notebook 05 |
| 2 | Interpretação corrigida | Calibração separada de ponto de operação; recall em 0,5 calibrado não mede isoladamente qualidade probabilística. Decisão histórica preservada. | decisão final, errata Etapa 5, protocolo e notebook |
| 3 | Implementada | Validador externo bloqueia mês/dia ausentes/invalidáveis, local desconhecido e bairro inválido/desconhecido antes de qualquer classificação. | `src/final5/validation.py`, testes novos |
| 4 | Preparada | Contrato seguro 1.1.0, opções controladas do vocabulário treinado, respostas de sucesso/erro, scores não calibrados e avisos. | `docs/contrato_inferencia_seguro.md` |
| 5 | Documentada e parcialmente mitigada | Proxies, raros, exclusão assimétrica, cobertura tardia, normalização e validade externa explícitos. O bloqueio reduz falhas de entrada; não corrige vieses aprendidos. | `docs/limitacoes_modelo_final.md` |
| 6 | Implementada | Git próprio, snapshot anterior às correções, exclusões seguras, registro antes/depois e versões separadas. | `.gitignore`, `docs/versionamento.md`, `reports/pos_auditoria/` |
| 7 | Documentada | 2025 foi explorado na Etapa 1, avaliado na Etapa 5 e consultado na auditoria; não é teste independente de v2. | README, limitações, protocolo final e errata |
| 8 | Implementada sem remover histórico | Baseline explicitamente legado, teste de acentuação identificado como histórico; novos testes cobrem alias do final. Classes serializadas mantidas no caminho original. | `src/ml/inference.py`, testes históricos e contrato seguro |

## 1. Referência simples e AUC

| Diagnóstico retrospectivo em 2025 | Accuracy | Macro F1 | AUC ROC |
| --- | --- | --- | --- |
| Tabela de frequências de roubo de 2023 por local/bairro agrupado | 69,28% | 67,27% | 0,7389 |
| MLP Dense64 v1.0.0 | 68,82% | 67,09% | 0,7412 |

Fonte: auditoria, A1. A MLP supera a classe majoritária (63,78% de acurácia), mas não demonstra ganho consistente sobre a tabela. A tabela foi construída depois do teste; não venceu um experimento independente e não foi adotada como novo classificador. AUC mede ordenação entre classes ao variar o limiar, sem depender do ponto binário 0,5; não é accuracy, Macro F1 ou qualidade de calibração. A pequena vantagem de AUC não invalida a conclusão de ganho não demonstrado.

## 2. Calibração e operação

O Platt ajustado em H1/2024 tinha inclinação positiva ≈0,9435 e intercepto ≈−0,0825. Em H2, Brier passou de 0,200356 para 0,199286, Log Loss de 0,583488 para 0,581087 e ECE10 de 3,81% para 2,29%. A auditoria mostra que 0,5 na escala calibrada equivalia a ≈0,5218 na original. A queda de recall de 3,49 pp e 2.508 classificações alteradas refletem esse deslocamento, não uma refutação dos ganhos probabilísticos.

A aplicação histórica do critério foi fiel ao protocolo, mas o critério misturava decisões diferentes. Calibração aproxima scores de frequências observadas; limiar define classe e compromisso de erros. O fato de a transformação preservar ordenação também não significa preservar as classes com o mesmo valor numérico de limiar. A v1.0.0 continua sem calibrador e com limiar 0,5; a manutenção não o adotou retroativamente.

Média sigmoid de roubo ≈44,31% versus prevalência 36,22% em 2025: excesso médio ≈8,10 pp. A auditoria mostra ECE igual a esse desvio, superestimação em todos os bins e AUC/inclinação semelhantes às de 2024. Isso sustenta diagnóstico de desajuste principalmente de nível associado à prevalência; não equivale a demonstrar invariância de todas as relações condicionais. Não foram gerados scores calibrados nem novos resultados de 2025 nesta revisão.

## 3–4. Comportamento do adaptador seguro

`SafeClassifier` valida antes de chamar `FinalPipeline`. Fixa a identidade do manifesto aprovado, usa o objeto original para normalização e carrega apenas a Dense64 final. Não importa o baseline.

- Mês inteiro 1–12 e dia inteiro 0–6 (segunda=0) são obrigatórios; None, bool, float, string numérica, NaN/inf e valores fora do domínio não chegam à rede.
- Local desconhecido é rejeitado, sem mapeamento silencioso para ausente. `OUTROS` mantém sua categoria.
- Bairro só numérico/sem letras, vazio, tipo incompatível, sentinela ou desconhecido é rejeitado. O usuário deverá selecionar explicitamente um valor do vocabulário.
- Bairro frequente e raro conhecido são distintos no contrato; raro recebe aviso. Local/bairro None são ausência explícita aceita com aviso e exemplos no treinamento. A aceitação técnica não valida sua confiabilidade para decisões reais.
- Não foi criada equivalência nova de acentos/abreviações. `TATUAPE`/`TATUAPÉ` continuam distintos; `JARDIM ÂNGELA`, ausente do vocabulário conhecido, é bloqueado, embora o histórico o aceitasse no bucket raro.
- Erros retornam `status=erro_validacao`, erros estruturados e nenhum score/classe. Sucesso traz classe, `scores_sigmoid`, versão do modelo/contrato, calibração falsa, grupos e avisos. Scores não representam chance de crime futuro.

O vocabulário vem do treinamento de 2023, sem leitura de datasets. Não é lista oficial de bairros; sua apresentação futura requer revisão, mantendo os valores canônicos. O validador não torna o modelo calibrado, não elimina erros de raros e não melhora métricas.

## 5. Vieses documentados

Ausência e OUTROS em local têm forte relação com o canal eletrônico e com a recodificação de 2024, sem vazamento comprovado. A frase de exclusividade da auditoria exige ressalva: sua tabela A3 inclui OUTROS presencial em 2025. A mudança de formulário é interpretação sustentada pelos cruzamentos do auditor, sem verificação adicional de versões oficiais nesta etapa.

Em via pública + bairro raro/desconhecido, o auditor encontrou 11.118 previsões constantes de roubo e 4.601 falsos positivos. O bucket junta 1.666 bairros de treino. Isso não produz ranking de risco territorial.

A exclusão de outras naturezas removeu proporcionalmente mais roubos (4,3%) que furtos (1,1%), sobretudo situações associadas a veículo. Fatos de 2025 registrados em 2026 não estão cobertos, ao contrário de parte dos registros tardios de 2023/2024. Intervalos históricos IID não incorporam dependência temporal ou variabilidade de treinamento. A validação interna de 2023 não testa adequadamente meses sem exemplos no treino; estabilidade de sementes mantém a ordem de lotes em 42. Ver limitações para detalhes.

## 6. Git, preservação e versões

O comando inicial de descoberta Git tentou resolver a pasta pessoal e falhou nesse contexto. Não existia `.git` próprio em GS-CNN. Foi executado `git init .` exclusivamente na raiz do projeto, e `rev-parse --show-toplevel` confirmou essa raiz. Não foram alterados o repositório superior ou configurações globais. Não há remoto nem publicação.

Snapshot **665d37b**, tag **snapshot-pos-auditoria-antes-correcoes**, criado antes das correções de conteúdo. Foram revisados 299 arquivos candidatos (5.559.724 bytes), com código/documentação/agregados/figuras/notebooks; o commit incluiu também o registro dessa revisão (300 arquivos). Dados, modelos binários, previsões individuais e logs foram excluídos. Nenhum CPF/chave comum foi encontrado pela varredura adicional; isso não substitui revisão humana para publicação futura. O `.gitignore` foi reforçado após o snapshot.

O inventário local anterior registra **408 arquivos**, incluindo artefatos não versionados. **395 permanecem idênticos; 13 têm revisões explícitas autorizadas**, com hash antigo/atual e motivo em `pos_auditoria/revisoes_autorizadas.json`. Para arquivos alterados, as verificações históricas exigem também que o hash antigo exista no blob da tag. Não há dispensa genérica de checksums. Os manifestos antigos não foram reescritos.

Modelo v1.0.0; software pos-auditoria-1.0.0; contrato seguro 1.1.0; pré-processador identificado pelo hash original; dados pelas versões/hashes já existentes; relatórios com publicação histórica e errata separada. Git criado agora não prova retroativamente a cronologia anterior. Hashes/timestamps de congelamento continuam autoatestados, conforme ressalva M5.

### Hashes preservados

| Artefato | SHA-256 |
| --- | --- |
| `models/final/modelo.keras` | `dadad1326e6ae58d0f26f7e69638a9283d46863c9ecb7d56e76e037b4940091c` |
| `models/final/preprocessador.joblib` | `b8b3cd3662505b872b5e6d34296fba53a5b1ce5e065811d128f0423aa050a524` |
| `models/final/manifesto.json` | `b992412335c69623bdf63c9341cefaa82e0a81ae73d7d32e110f2498faa8c532` |

Todos os arquivos congelados, oito fontes de inferência, datasets locais e resultados existentes são verificados contra o estado anterior. Nem `final5/pipeline.py`, `common.py`, o pré-processador serializado ou a classe referenciada por joblib foram modificados. O código de avaliação/métricas histórico também permanece idêntico.

## 7–8. Teste consumido e legado

2025 foi consultado na exploração inicial, na avaliação final e na auditoria independente. Não é teste independente para v2 ou para hipóteses concebidas depois desses diagnósticos. Futuras versões precisam de protocolo prévio e novo conjunto, por exemplo 2026 se disponível e adequado; não houve desenvolvimento de v2.

`src/ml/inference.py` foi marcado como histórico da Etapa 2, preservando seu comportamento. O teste de acentuação foi renomeado para explicitar esse escopo: ausência de equivalência automática no baseline não contradiz `local_alias=True` do final. Os testes novos verificam aliases reais do final e rejeição de equivalências não reconhecidas. Nenhuma classe serializada foi movida ou renomeada.

## Regressão executada

Runner específico: `PYTHONPATH=src python -m maintenance56.run_tests`. Logs separados em `reports/pos_auditoria/`; nenhum log histórico sobrescrito. Resultados detalhados em `testes_regressao.json`.

| Suíte | Executados | Falhas | Erros |
| --- | ---: | ---: | ---: |
| Integridade histórica | 8 | 0 | 0 |
| Pipeline baseline | 15 | 0 | 0 |
| Robustez histórica | 17 | 0 | 0 |
| Experimentos Etapa 4 | 17 | 0 | 0 |
| FinalPre | 18 | 0 | 0 |
| Contrato seguro novo | 30 | 0 | 0 |
| **Total consolidado** | **105** | **0** | **0** |

Os 83 testes históricos continuam presentes. Destes, 75 foram executados; os oito `FinalPost` de cache de 2025 foram separados e **não executados** nesta manutenção. Não são contabilizados como aprovações novas. A regressão histórica de integridade pode ler metadados/rótulos desse ano; não produz novas previsões, métricas experimentais ou seleção. Inferências executadas no final são apenas exemplos sintéticos; testes históricos também verificam amostras de 2024 e artefatos anteriores.

Execução preliminar do novo teste: 29 casos, 28 aprovados, zero falhas e um erro de premissa do teste (tentava tratar JARDIM ÂNGELA como conhecido). O adaptador já o rejeitava corretamente. O teste foi corrigido para usar duas grafias conhecidas e foi adicionado caso específico de rejeição; registro em `execucao_preliminar.json`. A suíte consolidada posterior tem 30 casos novos e zero erros. Não houve correção de pesos ou uso de 2025 para resolver esse erro.

As verificações de preservação nos testes foram adaptadas para conferir bytes originais no snapshot e bytes revisados autorizados. Os testes opcionais FinalPost conservam a verificação do cache; sua chamada de preservação, quando executados separadamente, reconhece o mesmo registro de revisão sem autorizar inferência. As funções históricas de preservação e o avaliador não foram editados.

## Arquivos afetados e evidências

Treze arquivos existentes revisados: `.gitignore`, `README.md`, `src/ml/inference.py`, os quatro testes de ML/robustez/experimentos/modelo final, `docs/decisao_modelo_final.md`, `docs/contrato_inferencia.md`, `docs/protocolo_teste_final.md`, `docs/recomendacoes_etapa6.md`, `reports/relatorio_etapa5.md`, `notebooks/05_avaliacao_final.ipynb`. O notebook recebeu apenas uma célula Markdown de errata; código e saídas originais não foram reexecutados/alterados.

Novos componentes: `src/final5/validation.py`, `src/maintenance56/` (integridade, registro de revisões e runner), `tests/test_contrato_inferencia_seguro.py`, documentos de contrato seguro/limitações/versionamento e este relatório. `reports/pos_auditoria/` contém revisão Git inicial, inventário local anterior, revisões autorizadas, execução preliminar, regressão e verificação final. Os logs/inventário completo local não são publicados.

## Hipóteses futuras e prontidão

H1 regressão logística; H2 normalização uniforme de bairros; H3 outra representação geográfica; H4 retirar/ciclar mês; H5 tratamento alternativo de ausência/OUTROS; H6 limiar por custo e calibração separados; H7 atualização de nível com dados recentes; H8 treino ampliado/janelas temporais; H9 diagnóstico por canal: **todas permanecem hipóteses não implementadas**. Exigem autorização, novo protocolo e teste não consumido. Nenhum experimento foi iniciado.

O contrato está **pronto para uma futura integração Python controlada**: identidade e integridade do final verificadas, validação bloqueante, opções derivadas do objeto, scores corretamente identificados e testes de regressão. Isso não torna o modelo adequado a operação policial nem elimina suas limitações. Interface HTTP/frontend, acessibilidade, seleção visual, revisão de apresentação das categorias e verificações de implantação pertencem à Etapa 6 e não foram implementadas.

Não há pendência impeditiva nas oito correções desta etapa. Artefatos binários e datasets permanecem locais e serão necessários para reproduzir o projeto em outro computador. Nenhuma melhoria de acurácia, Macro F1 ou calibração é reivindicada. Desenvolvimento encerrado na Etapa 5.6.
