# Consolidação acadêmica — 11/11/2026

O ponto de entrada atual é o [notebook completo](../notebooks/GS_Classificacao_MLP_Completo.ipynb).
Ele substitui cinco documentos por uma narrativa única de dez seções, sem novos
treinamentos, avaliação de 2025 ou alteração dos artefatos da Dense64.

## Mapa dos materiais históricos

| Notebook anterior | Conteúdo incorporado | Seções atuais |
| --- | --- | --- |
| `01_auditoria_exploracao.ipynb` | Proveniência, granularidade, filtros, classes, perdas, qualidade, amostra e prevenção de vazamento | 01–03 |
| `02_mlp_baseline.ipynb` | Pré-processamento, configuração, treinamento histórico, curvas, métricas, recarga e limites | 03–04 |
| `03_diagnostico_mlp.ipynb` | Erros, drift, permutação, confiança, raridade, robustez, sementes e hipóteses | 04, 06, 08 |
| `04_experimentos_arquiteturas.ipynb` | Blocos A/B/C, três MLPs, curvas internas/reajuste, sementes e comparação | 05–06 |
| `05_avaliacao_final.ipynb` | Congelamento, calibração, métricas/matriz de 2025, intervalos, grupos e errata | 07–08 |

O novo texto distingue o baseline histórico da Dense64 final, os resultados de
2024 dos de 2025, execução histórica de reprodução opcional e defeitos comprovados
de hipóteses. Os relatórios originais e suas figuras/JSON/CSV não foram reescritos.
As referências antigas nesses relatórios continuam sendo registros de sua data;
este mapa encaminha o leitor para o notebook atual.

Os arquivos antigos estão no commit anterior à consolidação:
`1da0bc4bb1b77a47b6475208aab63ded724a9eca`. Para consultar um deles:

```powershell
git show 1da0bc4bb1b77a47b6475208aab63ded724a9eca:notebooks/05_avaliacao_final.ipynb
```

O histórico guarda as saídas originais, inclusive a errata do notebook 05.
O snapshot/tag pós-auditoria também permanece intacto. Nenhum histórico foi
reescrito nem qualquer manifesto de ML foi atualizado.

## Requisitos acadêmicos

| Exigência | Evidência no notebook único |
| --- | --- |
| Exploração e tratamento | Seções 02–03: tabelas, painel exploratório e decisões |
| Implementação da baseline | Seção 04: fonte real de construção/compile/fit e resultados |
| Três arquiteturas | Seção 05: fonte real de Engine.run e chamadas ao orquestrador |
| Comparação de resultados | Seção 06: métricas de 2024, parâmetros e sementes |
| Curvas de treino/validação | Seções 04 e 06, distinguindo Q4 interno de reajuste completo |
| Matriz de confusão e teste final | Seção 07, somente leitura dos registros congelados |
| Análise crítica e auditoria | Seções 07–08: calibração, referências, proxies e limitações |
| Aplicação e conclusões | Seções 09–10: arquitetura web e uso responsável de IA |

As células padrão só leem agregados, fontes e hashes; não importam TensorFlow ou
desserializam joblib. A ausência dos binários é explicitada e não impede a leitura
ou execução acadêmica. As chamadas de treinamento ficam desativadas e exigem uma
worktree histórica preparada separadamente. Não há chamada ao avaliador de 2025.

Os geradores `src/{data,ml,diagnostics,experiments4,final5}/report.py` conservam
as rotinas de relatório, mas sua função `notebook()` agora encaminha ao documento
único. Não recriam os cinco notebooks antigos nem sobrescrevem o consolidado.
Os comandos completos de geração de relatórios continuam históricos e não são
um procedimento de manutenção da documentação atual.

## Preservação verificável

[consolidacao_manifesto.json](consolidacao_manifesto.json) registra, por caminho,
o commit e hash do arquivo anterior, a ação autorizada e o hash atual. Nas remoções,
registra o notebook consolidado como destino. Não substitui nem reescreve os
manifestos antigos ou o registro de correções 5.6.

A verificação de manutenção reconhece essa revisão explicitamente: confere o blob
anterior no Git, o histórico esperado (incluindo a errata 5.6 quando aplicável) e os
bytes atuais/destino. Não ignora genericamente arquivos ausentes ou alterações.
As fontes de inferência congeladas, incluindo referências históricas em
`src/ml/runtime.py`, permanecem intactas. `register_revisions.py` continua descrevendo
a revisão 5.6 original; não deve ser usado para regenerar esta consolidação.

Para validar a entrega, sem dados privados ou treinamento:

```powershell
python -m pip install nbformat nbclient ipykernel
python scripts/validar_documentacao.py
python scripts/validar_documentacao.py --executar
python tests/test_documentacao.py
```

O segundo comando executa em memória as células de leitura e os blocos opcionais
desativados, sem sobrescrever o `.ipynb`. Valida JSON, código, outputs, figuras,
links relativos/âncoras, métricas transcritas, versões dos badges, revisão histórica
e hashes da Dense64. Não executa os runners históricos de treino/teste final.

## Demonstração e apresentação pública

Em 11/11/2026, a [aplicação](https://spcrimeclassification.vercel.app/) e os endpoints
health/options/classify responderam 200; a classificação sintética coincidiu com
a Dense64 final. A [captura do README](images/aplicacao-publica.png) foi produzida
da página pública real nessa data. O estado “sem web”/“não publicado” dos relatórios
e guias antigos descreve sua época, não a situação atual. Esta revisão não fez deploy.

O README ganhou navegação progressiva, badges baseados nas versões reais, captura,
metodologia resumida, comparação conservadora e execução local transparente sobre
os binários ausentes no clone. Não foi inventada licença, identidade acadêmica,
superioridade da MLP ou estado de CI. Nome completo, RM e turma continuam sem
confirmação nos documentos acadêmicos consultados.

## Validação desta entrega

- Um único `.ipynb` versionado: 54 células, dez seções obrigatórias e 16 figuras.
- As 16 células de código executaram sem falhas; a execução foi repetida em cópia
  pública temporária sem pesos, datasets ou importação de TensorFlow.
- 86 links locais/âncoras conferidos; figuras PNG existentes; renderização local
  em 1280 e 390 pixels sem imagens quebradas ou transbordamento da página.
- Sete badges shields.io responderam 200 com SVG; GitHub, SSP-SP e FIAP responderam 200.
- Cinco testes editoriais aprovados, incluindo rejeição de destino adulterado,
  notebook antigo recriado e hash anterior forjado.
- 232 evidências históricas versionadas e os hashes de todos os arquivos
  congelados disponíveis conferem. As métricas foram lidas e comparadas com os
  registros existentes, sem reinferência ou recálculo do teste de 2025.
- Nenhuma modificação de aplicação ou implantação foi feita nesta tarefa;
  alterações de deploy que já estavam pendentes ficaram fora destes commits.

As prévias locais servem para revisão de legibilidade; a renderização final do
GitHub não foi publicada nesta tarefa. Os binários continuam fora do Git e os
dados acadêmicos pessoais (nome completo/RM/turma) permanecem sem confirmação.
