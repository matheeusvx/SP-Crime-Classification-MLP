# Auditoria técnica independente — Etapa 5.5

**Projeto:** Global Solution FIAP 2026.2 — classificação FURTO × ROUBO de celulares subtraídos (São Paulo, capital)
**Modelo auditado:** `gs-celulares-sp-dense64-v1.0.0` (299 → Dense64 ReLU → sigmoid, 19.265 parâmetros)
**Data da auditoria:** 09/11/2026
**Auditor:** Claude (auditoria somente leitura; nenhum arquivo existente foi alterado)

---

## 1. Parecer

**O modelo e os números publicados são autênticos e reproduzíveis; a interpretação deles é que precisa de correção.**

1. **Integridade confirmada.** Todos os hashes (manifesto, artefatos, código de inferência, datasets, resultados, 344 arquivos históricos) conferem. Recarreguei o modelo congelado e reproduzi as 156.168 probabilidades de 2025 com diferença máxima **0,0**. Matriz de confusão, métricas e intervalos foram recalculados de forma independente e batem até a última casa.
2. **Não encontrei vazamento comprovado.** Nenhum atributo derivado do rótulo entra no modelo, o pré-processador foi ajustado só em 2023 e não há boletim repetido entre anos.
3. **A MLP não demonstra vantagem sobre uma tabela de frequências.** Uma referência descritiva — frequência de roubo em 2023 por (tipo de local, bairro) — obtém em 2025 acurácia 69,28 % e Macro F1 67,27 %, contra 68,82 % e 67,09 % da rede. O projeto só comparou a rede com a classe majoritária, o que faz o ganho parecer maior do que é.
4. **A rejeição da calibração foi metodologicamente incorreta.** O critério de recall no limiar 0,5 mediu um deslocamento de limiar, não a qualidade da calibração.
5. **O aumento do ECE (2,71 % → 8,10 %) é mudança de prevalência, não perda de discriminação.** O ECE de 2025 é exatamente a diferença entre probabilidade média prevista e prevalência real; AUC e inclinação de calibração ficaram estáveis.
6. **`tipo_local` ausente/`OUTROS` é um artefato do canal de registro** (Delegacia Eletrônica), não uma característica do local. Responde por cerca de 1,9 pp da acurácia de 2025.
7. **O contrato de inferência tem defeitos que precisam ser tratados antes da aplicação web** (seção 4, achados A4 e M1).

**Recomendação:** manter o modelo v1.0.0 congelado como está, corrigir a narrativa do relatório e o contrato de inferência, e tratar qualquer melhoria como versão nova com protocolo próprio. O teste de 2025 já foi consumido (inclusive por esta auditoria) e não serve mais como avaliação independente de uma nova versão.

---

## 2. Escopo, método e limitações

**O que fiz**

- Li todo o código de `src/` (data, ml, diagnostics, experiments4, final5), os testes, os protocolos e os relatórios das cinco etapas.
- Verifiquei os SHA-256 de manifesto, artefatos, fontes, datasets e resultados; comparei horários de modificação dos arquivos com os timestamps registrados.
- Consultei os Parquet intermediários (linhas originais da SSP) e processados com DuckDB, em memória.
- Recarreguei modelo e pré-processador congelados e refiz a inferência de 2023, 2024 e 2025 **em memória**, sem gravar nada, para confirmar que os pesos produzem as previsões salvas.
- Recalculei métricas, ECE, intervalos e análises por subgrupo a partir de `reports/etapa5/private/previsoes_2025.npz`.

Os quatro scripts de auditoria estão fora do projeto, em
`C:\Users\Sucesso\AppData\Local\Temp\claude\1c4e4ec26f912e7d\5082bee7-c8ea-4d55-990a-0f00e85a8917\scratchpad\` (`a1.py` a `a4.py`).

**Limitações e ressalvas**

- **Os XLSX originais (`D:\CelularesSubtraidos_*.xlsx`) não foram acessados.** A fidelidade do parser OOXML e a proveniência SSP não foram verificadas; a auditoria parte dos Parquet intermediários.
- **Esta auditoria abriu 2025 uma segunda vez.** A reinferência serviu só para reprodução, e os rótulos de 2025 foram usados em diagnósticos descritivos. Nada foi selecionado nem ajustado, mas isso reforça que 2025 não é mais um conjunto cego.
- **A referência por tabela de frequências foi calculada por mim, depois do teste.** É um diagnóstico, não um candidato validado. Não executei nenhum treinamento (nem regressão logística).
- **A ordem temporal dos eventos depende de timestamps gravados pelo próprio pipeline e de horários de arquivo.** Não há histórico de versão (ver M5), então "congelado antes do teste" é consistente com as evidências, mas não é demonstrável de forma independente.
- Notebooks não foram reexecutados. A suíte de testes não foi reexecutada (ela grava logs em `reports/`).

---

## 3. O que foi verificado e está correto

| Item | Resultado | Evidência |
|---|---|---|
| Manifesto e sidecar SHA-256 | Conferem | `manifesto.json` = `b992…c532` |
| 4 artefatos congelados, 8 fontes de inferência, 3 datasets, 4 artefatos de origem `B64_full_s42` | Todos conferem | recálculo de hash |
| 11 arquivos de resultado de `avaliacao_unica.json` | Todos conferem | recálculo de hash |
| Preservação das etapas anteriores | 168 (Etapa 4) e 344 (Etapa 5) arquivos sem alteração | `preservacao.json` |
| Pesos após a avaliação | `modelo.keras` e `preprocessador.joblib` com horário 22:20:40 UTC (cópia do treino da Etapa 4), anteriores ao congelamento 22:42:06 e à inferência 22:46:16 | horários de arquivo |
| Reprodução das previsões | 2025: diferença máxima 0,0; 2024: 0,0 | reinferência em memória |
| Arquitetura | 299 → 64 → 1; 19.200 + 65 = 19.265 parâmetros; pesos finitos; nenhum neurônio morto | `model.summary()` |
| Matriz de confusão 2025 | TN 71.598, FP 28.009, FN 20.691, TP 35.870 | recálculo |
| Accuracy / Macro F1 / Bal. acc. | 68,82 % / 67,09 % / 67,65 % | recálculo |
| Precision / Recall de roubo | 56,15 % / 63,42 % | recálculo |
| Brier / Log Loss / ECE10 | 0,20055 / 0,58351 / 8,10 % | recálculo |
| IC 95 % da acurácia | 68,59–69,04 % (coincide com o intervalo de Wald) | recálculo com a mesma semente |
| Rótulos | Só `Furto (art. 155)` → 0 e `Roubo (art. 157)` → 1; as outras duas rubricas com "furto" (art. 156 e art. 25) ficaram corretamente fora | consulta às linhas originais |
| Chave do boletim | 995.565 boletins tanto por `NOME_DELEGACIA` quanto por `ID_DELEGACIA`; sem colisão | consulta |
| Disjunção entre anos | 505.187 chaves únicas, cada uma em um único ano do fato | consulta |
| Ajuste do pré-processador só em 2023 | 190.124 registros; `OUTROS` com 12 exemplos, igual à contagem de 2023 | atributos do objeto |
| Atributos de entrada | mês, dia da semana, tipo de local, bairro — nenhum derivado da natureza criminal | código e manifesto |

Toda a base é `CONSUMADO`, `Subtraído`, `Telecomunicação`: não há tentativa nem objeto de outro tipo misturado.

---

## 4. Achados por severidade

Classificação de natureza usada: **defeito comprovado**, **risco plausível**, **mudança de distribuição**, **associação legítima**, **hipótese**.

Nenhum achado crítico (que invalide os números publicados) foi encontrado.

### Severidade ALTA

#### A1. A MLP não supera uma referência trivial, e o projeto não tem essa referência
*Natureza: lacuna metodológica comprovada.*

A única referência do projeto é a classe majoritária (63,78 %), contra a qual a rede ganha 5,03 pp. Não existe regressão logística, nem tabela de frequências, nem AUC em nenhum relatório.

Referência descritiva calculada nesta auditoria: frequência de roubo em 2023 por (tipo de local, bairro agrupado como no pré-processador), limiar 0,5.

| Ano | Modelo | Accuracy | Macro F1 | Recall roubo | AUC | Brier |
|---|---|---|---|---|---|---|
| 2024 | Tabela de frequências | 68,53 % | 67,58 % | 61,12 % | 0,7417 | 0,2029 |
| 2024 | MLP Dense64 | 68,51 % | 67,69 % | 62,53 % | 0,7448 | 0,2016 |
| 2025 | Tabela de frequências | 69,28 % | 67,27 % | 61,37 % | 0,7389 | 0,2006 |
| 2025 | MLP Dense64 | 68,82 % | 67,09 % | 63,42 % | 0,7412 | 0,2005 |

As duas concordam na classe em 93,8 % dos boletins de 2025. As diferenças (≤ 0,5 pp) são do tamanho da variação entre sementes e meses, portanto **não há ganho demonstrado da rede**.

Outras evidências na mesma direção:

- **Fora de via pública (21,9 % de 2025) a rede prevê furto em 97,5 % dos casos**: acurácia 87,99 %, contra 88,04 % de simplesmente responder "furto". Contribuição nula.
- **Em via pública**, acurácia 63,45 % contra 56,99 % da classe majoritária local. Todo o ganho vem daqui, pelo bairro.
- **Mês e dia da semana explicam 1,4 % e 0,5 %** da variância do logit previsto; tipo de local 52 % e bairro 60 %.
- **Todas as arquiteturas da Etapa 4 empatam**: Dense32, Dense64 e 64→32 ficam entre 67,5 % e 67,7 % de Macro F1 em 2024.
- **Teto dos atributos**: mesmo um oráculo que conhecesse a classe majoritária de cada combinação exata dos quatro atributos em 2025 chegaria a 79,2 % (limite otimista, com sobreajuste a 41.685 contextos); com tipo de local + bairro, 72,3 %.

Conclusão: o gargalo é a informação contida nos atributos, não a capacidade da rede.

#### A2. A calibração foi rejeitada por um critério que mede limiar, não calibração
*Natureza: defeito metodológico comprovado.*

O protocolo exigia que o recall de roubo **no limiar 0,5** não caísse mais de 1 pp após Platt. O Platt ajustado (inclinação 0,9435; intercepto −0,0825) é uma transformação monótona: não muda a ordenação de nenhum boletim.

- Limiar 0,5 na probabilidade calibrada equivale a **0,5218** na probabilidade original.
- As 2.508 "mudanças de classificação" são exatamente os boletins com probabilidade original entre 0,5000 e 0,5218.
- O recall "perdido" (63,3 % → 59,8 %) é o recall da rede original no limiar 0,5218 (59,5 % em 2024 inteiro).
- Para manter as classificações idênticas bastaria usar limiar **0,479** na escala calibrada.

Calibrar e escolher o ponto de operação são decisões independentes; o protocolo as fundiu. O Platt cumpria todos os critérios probabilísticos (Brier, Log Loss, ECE10 de 3,81 % para 2,29 %).

Ressalva importante: adotar aquele Platt **não teria resolvido 2025**. Aplicado como diagnóstico, reduziria o ECE de 8,10 % para 6,60 %, porque o problema de 2025 é a queda de prevalência (M4), posterior ao período de ajuste.

Consequência prática: a saída é rotulada `probabilidades_calibradas=False`, o que é honesto. Mas a justificativa registrada em `docs/decisao_modelo_final.md` e no relatório ("recall caiu 3,49 pp") está errada e deve ser corrigida.

A instabilidade do recall no limiar 0,5 aparece em todo o projeto: entre três sementes da mesma Dense64 (validação interna) o recall varia de 63,8 % a 66,7 %, com Macro F1 praticamente idêntico. Há muita massa de probabilidade junto a 0,5, então **qualquer regra baseada em ±1–2 pp de recall nesse limiar decide por ruído**.

#### A3. `tipo_local` ausente e `OUTROS` são artefatos do canal de registro
*Natureza: risco plausível de proxy administrativo + mudança de distribuição comprovada. Não é vazamento comprovado.*

Evidência nova (não consta nos relatórios anteriores): cruzando com `NOME_DELEGACIA`, a ausência e o `OUTROS` existem **apenas em boletins da Delegacia Eletrônica**.

| Ano (capital, linhas furto/roubo) | Canal | Furto: ausente | Furto: OUTROS | Roubo: ausente | Roubo: OUTROS |
|---|---|---|---|---|---|
| 2023 | Eletrônica | 13,6 % | 0,0 % | 2,1 % | 0,0 % |
| 2023 | Presencial | 0,0 % | 0,0 % | 0,0 % | 0,0 % |
| 2024 | Eletrônica | 5,4 % | 8,6 % | 0,9 % | 1,3 % |
| 2025 | Eletrônica | 0,0 % | 12,8 % | 0,0 % | 2,2 % |
| 2025 | Presencial | 0,0 % | 0,9 % | 0,0 % | 0,2 % |

A troca acontece no 2º trimestre de 2024: ausência cai de 7,96 % para 0,04 % e `OUTROS` sobe de 0,07 % para 7,5 %. A taxa de roubo do grupo fica igual (≈ 10 % antes, ≈ 8–9 % depois). É o mesmo fenômeno com outro nome — uma mudança no formulário eletrônico.

Diagnóstico por categoria:

- **Vazamento comprovado: não.** O campo não é derivado da rubrica.
- **Proxy administrativo: plausível e bem sustentado.** O valor informa *como* o boletim foi preenchido, não *onde* o fato ocorreu. É o mesmo tipo de padrão que levou, corretamente, à exclusão de hora/período na Etapa 1 (hora ausente em 75 % dos furtos e 11 % dos roubos); o critério não foi aplicado de forma consistente a `tipo_local`.
- **Mudança de distribuição: comprovada.**
- **Impacto medido:** em 2025 esse grupo tem 11.969 boletins (7,7 %), com acurácia 91,65 %. Sem ele, a acurácia do modelo é **66,92 %** em vez de 68,82 %.
- **O modelo acertou `OUTROS` por estrutura, não por aprendizado.** A categoria tinha 12 exemplos no treino. A rede prevê furto para quase tudo que não é via pública, e `OUTROS` herdou esse comportamento (probabilidade ≈ 0,07–0,13). Funcionou em 2025, mas não é robustez demonstrada.

A experiência A1 da Etapa 4 (sem `tipo_local`: Macro F1 64,35 % contra 67,69 % em 2024) mede o campo inteiro, e a maior parte dessa diferença é a associação legítima via pública × demais locais.

#### A4. O contrato de inferência aceita entradas que ativam pesos nunca treinados ou sinais errados
*Natureza: defeito comprovado (não afeta as métricas de 2025; afeta a aplicação web).*

| Entrada | Comportamento observado | Problema |
|---|---|---|
| `mes=None` ou `dia_semana=None` | Aceito; probabilidade muda de 0,255 para 0,366 / 0,323 no exemplo-base | As colunas `mes___AUSENTE__` e `dia_semana___AUSENTE__` têm **zero exemplos no treino**: os pesos são os da inicialização aleatória. O aviso emitido não impede a resposta. |
| `tipo_local` desconhecido (ex.: "PRAIA") | Tratado como ausente → 0,060 | "Desconhecido" vira o sinal mais forte de furto do modelo, que por sua vez é um artefato do canal eletrônico (A3). Um erro de digitação gera "FURTO" com alta confiança. |
| `bairro` só com dígitos (ex.: "123") | Tratado como bairro ausente → 0,742 | Bairro ausente é um grupo de 633 exemplos com 66 % de roubo. |

Exemplo-base: mês 5, quarta-feira, VIA PÚBLICA, BELA VISTA → 0,2554.

### Severidade MÉDIA

#### M1. Normalização de bairro inconsistente
*Natureza: defeito comprovado, impacto pequeno e medido.*

Tipo de local recebe equivalência automática de acentuação; bairro só tem uma lista manual de 16 pares. Consequências verificadas:

- **Dez bairros frequentes ocupam duas colunas One-Hot cada**, por diferença de acento: TATUAPE (1.441) / TATUAPÉ (1.091), BUTANTA (946) / BUTANTÃ (599), SANTA CECILIA (1.932) / SANTA CECÍLIA (100), BRASILANDIA / BRASILÂNDIA, LIMAO / LIMÃO, JAGUARE / JAGUARÉ, JARAGUA / JARAGUÁ, CANGAIBA / CANGAÍBA, JARDIM DAS ACACIAS / ACÁCIAS, CIDADE ANTÔNIO ESTEVÃO / ESTÊVÃO DE CARVALHO.
- **Grafias acentuadas de bairros frequentes caem no grupo raro**: 227 boletins em 2025 (VILA CARRÃO 67, NOSSA SENHORA DO Ó 28, TREMEMBÉ 20, BELÉM 19…).
- **O mesmo bairro recebe respostas diferentes conforme a grafia**: `JARDIM ANGELA` → 0,780 (ROUBO); `JARDIM ÂNGELA` → 0,639; `JD ANGELA` → 0,639.

O efeito sobre as métricas de 2025 é pequeno (0,15 % dos boletins), mas na aplicação web o usuário digita o bairro, e a resposta depende do acento.

#### M2. Bairros raros: previsão constante de ROUBO em via pública
*Natureza: consequência da representação e dos dados de treino; não é erro de implementação.*

| 2025 | Boletins | Roubo real | Previsto ROUBO | FP | FPR |
|---|---|---|---|---|---|
| Bairro frequente | 142.253 | 34,7 % | 36,7 % | 23.198 | 25,0 % |
| Raro conhecido | 12.986 | 51,4 % | 84,0 % | 4.548 | 72,0 % |
| Desconhecido | 389 | 58,1 % | 87,9 % | 126 | 77,3 % |
| **Via pública + raro/desconhecido** | **11.118** | **58,6 %** | **100 %** | **4.601** | **100 %** |

- O grupo raro representa 8,6 % dos boletins e **16,7 % de todos os falsos positivos**.
- **Causa:** 1.666 bairros distintos compartilham uma única coluna. Em 2023 esse grupo tinha 63,4 % de roubo (68,6 % em via pública); a rede aprendeu um único peso e responde ROUBO para todos. O comportamento é idêntico em 2023, 2024 e 2025 — não há inconsistência de código.
- **Com a queda da prevalência**, o grupo passou a 51,4 % de roubo em 2025, e a acurácia nele caiu de 69,1 % para 62,6 %.
- **Componente administrativo parcial:** bairros raros são duas vezes mais comuns em registros presenciais (14,2 %) do que eletrônicos (7,3 %), e roubos são mais registrados presencialmente (48,3 % contra 33,4 %). Porém, dentro do mesmo canal o grupo raro ainda tem mais roubo (47,0 % contra 32,4 % no eletrônico), então a associação geográfica é em boa parte real.

#### M3. O atributo `mes` foi mantido sem evidência válida
*Natureza: fragilidade metodológica comprovada; efeito sobre desempenho é hipótese.*

- A validação interna (treino jan–set, validação out–dez de 2023) **não pode avaliar o mês**: as colunas de outubro a dezembro nunca são treinadas. O próprio protocolo reconhece.
- Nessa validação, o modelo sem mês (A3) teve Macro F1 igual ou maior (68,21 % contra 68,08 %) e era o escolhido pela regra de desempate registrada.
- A escolha foi revertida por uma regra de recall (A3 perdia 3,9 pp), diferença da mesma ordem da variação entre sementes (2,9 pp).
- A3 não foi reajustado em 2023 completo nem comparado em 2024.
- O efeito de mês é aprendido de **um único ano**: não é possível separar sazonalidade de particularidades de 2023 (janeiro/2023 teve 49,4 % de roubo; setembro, 39,7 %).

#### M4. A piora de calibração em 2025 é mudança de prevalência
*Natureza: mudança de distribuição comprovada.* O relatório da Etapa 5 trata como "hipótese consistente, não causa demonstrada"; a evidência permite afirmar mais.

| | 2023 (treino) | 2024 | 2025 |
|---|---|---|---|
| Prevalência de roubo | 44,03 % | 42,07 % | 36,22 % |
| Probabilidade média prevista | 44,51 % | 44,72 % | 44,31 % |
| Diferença | −0,5 pp | −2,65 pp | **−8,10 pp** |
| ECE10 | — | 2,71 % | **8,10 %** |
| AUC | — | 0,7448 | 0,7412 |
| Inclinação de calibração (diagnóstico) | — | 0,954 | 0,951 |
| Intercepto de calibração (diagnóstico) | — | −0,138 | −0,415 |

- **O ECE de 2025 é idêntico, até a 6ª casa, à diferença entre média prevista e prevalência** (0,080964): todos os intervalos superestimam roubo no mesmo sentido. É erro de nível, não de forma.
- **A discriminação não mudou** (AUC e inclinação estáveis). Calibração e decisão binária são, portanto, problemas separados: a decisão continua com a mesma qualidade de ordenação; o nível das probabilidades é que ficou defasado.
- A queda de roubo ocorre dentro de via pública (51,1 % → 49,7 % → 43,0 %) e em quase todos os tipos de local: é mudança real da proporção de classes na base, não efeito de recodificação.
- Acurácia subiu (+0,31 pp) e precision de roubo caiu (−6,4 pp) pelo mesmo motivo.

Detalhe: o intervalo 0,9–1,0 tem só 34 boletins com 44 % de roubo. Sem peso estatístico, mas "confiança ≥ 90 % em roubo" não é confiável.

#### M5. Congelamento: consistente, mas autoatestado
*Natureza: fragilidade de rastreabilidade. Não há indício de adulteração.*

- **Não existe controle de versão.** O repositório Git detectado é a pasta pessoal `C:\Users\Sucesso`, sem nenhum commit. Toda a prova de ordem temporal vem de JSON e horários gravados pelo próprio pipeline.
- **`manifesto.sha256` fica ao lado do manifesto**: protege contra alteração acidental, não contra regeneração.
- **`src/final5/evaluate.py` foi modificado às 22:45:53 UTC** — depois do congelamento (22:42:06) e dos testes prévios (22:45:19), e 18 s antes da avaliação (22:46:11). O relatório declara a causa (importação de `Path` ausente). A explicação é coerente com o código: o erro ocorreria na linha 67, antes da criação de `avaliacao_unica.json` e antes de carregar 2025. Não é verificável de outra forma.
- **O código de avaliação e de métricas não está na lista de hashes do manifesto** nem em `preservacao.json`; só é registrado no início da avaliação.
- `tests/test_modelo_final.py` e `run_tests.py` têm horário 22:44:36–38, posteriores ao congelamento.
- "Uma única avaliação" depende de `avaliacao_unica.json` não ter sido apagado; não há registro externo.

O que sustenta a conclusão favorável: pesos com horário anterior a tudo, cópia byte a byte de um treino da Etapa 4 que nunca leu 2025, e reprodução exata das previsões.

#### M6. Exclusão assimétrica de roubos na Etapa 1
*Natureza: viés de seleção comprovado e não documentado; não é erro de rótulo.*

Boletins com qualquer natureza além de furto/roubo são excluídos (`outras_naturezas_associadas`). Na capital, isso remove **4,3 % dos boletins de roubo e 1,1 % dos de furto**. A causa dominante é `Localização/Apreensão e Entrega de veículo` (4.785 boletins de roubo): roubos de veículo em que o celular foi levado junto.

A regra é defensável para a pureza do rótulo e não proponho revertê-la. Mas o domínio do modelo passa a sub-representar roubos de celular associados a veículo, e isso deve constar nas limitações.

#### M7. Os intervalos de confiança subestimam a incerteza
*Natureza: limitação de método (parcialmente declarada no relatório).*

O sorteio multinomial das quatro células é matematicamente correto e equivalente a reamostrar boletins independentes; por isso coincide com o intervalo de Wald (±0,23 pp). Ele ignora dependência temporal e variação de treino. A acurácia mensal de 2025 tem desvio-padrão de 1,25 pp (67,2 % a 71,1 %); um intervalo por blocos mensais seria da ordem de **68,0–69,6 %**. Não há intervalo para Brier, Log Loss ou ECE.

### Severidade BAIXA

| # | Achado | Natureza | Evidência |
|---|---|---|---|
| B1 | Rótulos de 2025 foram consultados na Etapa 1 | Exposição comprovada, efeito conservador | `qualidade_temporal_atributos.csv` e `classes_por_ano.csv` trazem classe × ano incluindo 2025; `distribuicao_tipo_local.csv` agrega os três anos por classe. A decisão tomada com base nisso (retirar hora/período) reduz desempenho, não o infla. |
| B2 | 2025 não tem registros tardios | Assimetria entre conjuntos | 0,8 % dos fatos de 2023 e 1,06 % dos de 2024 vêm de arquivos de anos seguintes (com menos roubo: 34,5 %). Os de 2025 registrados em 2026 não existem na base. |
| B3 | Código duplicado e contratos conflitantes | Risco de integração | Duas classes de pré-processamento (`ml.preprocessing` e `experiments4.preprocessing`) e duas de inferência. `src/ml/inference.py` ainda carrega o baseline antigo (`models/mlp_baseline.keras`). `test_acento_local_nao_e_equivalencia_automatica` afirma o oposto do comportamento do modelo final. |
| B4 | "Estabilidade em três sementes" subestima a variância | Limitação | A ordem dos lotes usa sempre a semente 42; só a inicialização muda. Desvio de Macro F1 de 0,02 pp. |
| B5 | Conflito de atributo dentro do boletim vira ausente | Imprecisão pequena | 184 (tipo de local) e 470 (bairro) boletins elegíveis; confunde "conflitante" com "não informado". |
| B6 | Filtro geográfico só por `NOME_MUNICIPIO_CIRC` | Associação correta, ruído residual | 325 linhas de 2025 (0,15 %) com circunscrição São Paulo e `CIDADE` diferente; 167 no sentido inverso. Decisão documentada e razoável. |
| B7 | Classe final chama-se `ExperimentalPreprocessor` e vive em `experiments4` | Manutenção | O artefato de produção depende de um módulo de experimento. |
| B8 | Época fixa escolhida sobre curva plana | Observação | `val_loss` interno: 0,5885 → 0,5887 → 0,5871 → 0,5875. A rede converge na primeira época; "3 épocas" é indiferente. |

---

## 5. Diagnóstico de vazamento — resumo

| Possível fonte | Diagnóstico | Evidência |
|---|---|---|
| Rubrica, conduta, desdobramento, artigo | **Sem vazamento** | Não estão entre as entradas |
| Identificadores (delegacia, nº BO, chave) | **Sem vazamento** | Só em metadados separados |
| Pré-processamento com dados de validação/teste | **Sem vazamento** | Ajuste restrito a 2023, verificado no objeto salvo |
| Boletins repetidos entre conjuntos | **Sem vazamento** | Chaves únicas, um ano por chave |
| Lista de equivalências de bairro | **Sem vazamento** | Fixa no código; ativada só por grafias de 2023 |
| Limiar de frequência de bairro (50) | **Sem vazamento** | Contagens de 2023 |
| Contextos idênticos (mesmos 4 atributos) em anos diferentes | **Associação legítima** | Inerente a atributos de baixa cardinalidade |
| Via pública × demais locais | **Associação legítima** | Roubo exige contato com a vítima; padrão igual nos dois canais |
| `tipo_local` ausente / `OUTROS` | **Risco plausível de proxy** + **mudança de distribuição** | Só no canal eletrônico; ≈ 1,9 pp de acurácia (A3) |
| Grupo de bairros raros | **Associação legítima com componente administrativo plausível** | M2 |
| Hora / período | **Risco identificado e evitado** | Excluídos na Etapa 1 |
| Estatísticas de 2025 na Etapa 1 | **Exposição sem ganho indevido** | B1 |
| Uso de 2024 em parada antecipada, diagnóstico e escolha | **Declarado**; 2024 não é avaliação independente | Protocolos das Etapas 2–5 |

---

## 6. Arquitetura MLP

**Implementação: correta.** Dimensão de entrada 299 = 13 (mês) + 8 (dia) + 29 (local) + 249 (bairro). Uma camada oculta de 64 ReLU, saída sigmoid, entropia cruzada binária, Adam 0,001, lote 256, 3 épocas fixas, inicialização Glorot uniforme, sem regularização, limiar 0,5. Sem problema numérico; a matriz esparsa é densificada um lote por vez (5,4 MiB em CSR contra 178 MiB densa).

**Adequação: a rede é maior do que o problema exige, sem prejuízo.**

- Com quatro atributos categóricos em One-Hot, uma camada oculta só acrescenta interações entre categorias em relação a um modelo linear. A referência de A1 indica que o sinal é essencialmente a frequência por (local, bairro).
- 19.265 parâmetros para um sinal dominado por duas variáveis. Dense32 (9.633) empata.
- Convergência em uma época; diferença treino–validação pequena (69,75 % contra 68,51 %): não há sobreajuste relevante nem subajuste que mais camadas resolvam.
- Limitações do One-Hot aqui: bairros raros colapsados em uma coluna (M2), grafias como categorias distintas (M1), mês sem ordem nem ciclicidade e aprendido de um só ano (M3), categorias novas sem representação.

**Não recomendo aumentar profundidade.** Também não afirmo que um modelo mais simples seja melhor: afirmo que não foi testado e que a evidência disponível sugere empate.

---

## 7. Oportunidades de otimização

**Correção e robustez**

1. Rejeitar `None` em mês e dia da semana, em vez de responder com pesos não treinados.
2. Distinguir "tipo de local desconhecido" de "ausente" na resposta (hoje ambos produzem o mesmo sinal forte de furto).
3. Unificar a normalização de acentos de bairro com a de tipo de local (exige novo ajuste do pré-processador → nova versão).
4. Na aplicação web da v1.0.0, usar listas de seleção com as categorias conhecidas pelo modelo, eliminando texto livre sem alterar o modelo.

**Simplificação**

5. Manter uma única classe de pré-processamento e uma única de inferência; marcar `src/ml/inference.py` e o baseline como legados.
6. Mover a classe do pré-processador final para um módulo estável (exige cuidado: o `joblib` referencia o caminho atual do módulo).
7. Remover ou atualizar o teste que contradiz o comportamento final de acentuação.

**Desempenho computacional** (ganhos pequenos; o modelo já é leve)

8. `predict_batched` percorre lotes de 256 em laço Python; lotes de alguns milhares reduziriam o tempo da avaliação completa (≈ 12 s hoje). Irrelevante para requisições individuais.
9. A normalização registro a registro em Python é adequada para o volume atual.

**Testes ausentes**

10. Nenhum teste verifica que grafias equivalentes de bairro produzem a mesma resposta.
11. Nenhum teste compara o modelo com uma referência simples.
12. Nenhum teste cobre colunas sem exemplos de treino além de emitir aviso.
13. Os testes de "bloqueio de 2025" verificam que o carregador recusa o ano, não que nenhuma estatística de 2025 foi consultada.

---

## 8. Plano priorizado

### 8.1 Correções obrigatórias (não alteram pesos, pré-processador nem limiar)

| Prioridade | Correção | Achado | Tipo de mudança |
|---|---|---|---|
| 1 | Acrescentar ao relatório final a comparação com referência simples e o AUC; reescrever a conclusão: a rede supera a classe majoritária, mas não demonstra ganho sobre uma tabela de frequências | A1 | Documentação |
| 2 | Corrigir a justificativa da calibração: a rejeição decorreu de um critério de limiar; registrar que a saída não é calibrada e superestima roubo em ≈ 8 pp em 2025 | A2, M4 | Documentação |
| 3 | Antes da Etapa 6: recusar mês/dia ausentes e tratar tipo de local desconhecido de forma explícita na camada de aplicação | A4 | Código da aplicação (fora dos artefatos congelados) |
| 4 | Na interface web: campos de seleção com as categorias do manifesto; não exibir a probabilidade como "chance", apenas classe estimada com aviso | A4, M1, M4 | Projeto da Etapa 6 |
| 5 | Documentar nas limitações: artefato do canal eletrônico em `tipo_local`; exclusão assimétrica de roubos; grupo de bairros raros sempre previsto como roubo em via pública | A3, M2, M6 | Documentação |
| 6 | Criar repositório Git próprio do projeto, com commit e tag do estado atual | M5 | Infraestrutura |
| 7 | Registrar que 2025 foi consultado na Etapa 1 e nesta auditoria; qualquer versão futura precisa de novo conjunto de teste | B1 | Documentação |
| 8 | Desativar ou marcar como legado `src/ml/inference.py` e o teste contraditório | B3 | Código (requer autorização) |

### 8.2 Hipóteses de melhoria (exigem autorização, novo protocolo e validação experimental)

Nenhuma destas é uma melhoria comprovada. Como 2025 já foi consumido, a validação teria de usar divisões temporais dentro de 2023–2024 para seleção e **dados novos (2026) para teste**.

| # | Hipótese | O que testaria | Motivação |
|---|---|---|---|
| H1 | Regressão logística sobre o mesmo One-Hot iguala a MLP | Necessidade da camada oculta | A1 |
| H2 | Normalização uniforme de acentos e abreviações de bairro reduz o grupo raro e as inconsistências | Macro F1 e FPR no grupo raro | M1, M2 |
| H3 | Substituir bairro em texto livre por distrito oficial ou por célula de latitude/longitude (colunas existem na base original) | Elimina grafias e o grupo "raro" heterogêneo | M2 |
| H4 | Retirar `mes` ou usar codificação cíclica | Comparação válida em 2024 com ajuste em 2023 completo | M3 |
| H5 | Fundir `tipo_local` ausente e `OUTROS`, ou retirar ambos como sinal | Sensibilidade ao artefato do canal | A3 |
| H6 | Escolher o limiar por custo explícito de erro e calibrar separadamente | Separar ponto de operação de calibração | A2 |
| H7 | Recalibrar o nível com dados recentes (correção de prevalência) | ECE sob mudança de prevalência | M4 |
| H8 | Treinar com 2023 + 2024 e validar em janelas deslizantes | Robustez temporal; efeito de mês com dois anos | M3, M4 |
| H9 | Avaliar separadamente por canal de registro (apenas diagnóstico; o canal não deve ser entrada) | Quanto do sinal é do fato e quanto do formulário | A3, M2 |

---

## 9. Encerramento

A auditoria termina aqui. Nenhum código, peso, pré-processador, dataset ou relatório existente foi modificado; o único arquivo criado no projeto é este. Nenhuma correção foi implementada: todas dependem de avaliação e autorização separadas.
