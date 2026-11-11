# Reprodução da Etapa 2

Esta etapa treina uma única MLP, exclusivamente com fatos de 2023 e validação de 2024. Os 156.168 registros de 2025 são verificados apenas estruturalmente e ficam bloqueados para transformação preditiva, inferência e métricas. O carregador não retorna 2025 e a função de avaliação rejeita esse ano. Não existe frontend ou API HTTP.

## Ambiente separado

Python 3.12, ambiente virtual próprio para ML. Não é necessário alterar ou executar novamente a engenharia da Etapa 1:

```powershell
python -m venv .venv-ml
.venv-ml\Scripts\python.exe -m pip install -r requirements-ml.txt
$env:PYTHONPATH='src'
$env:PYTHONHASHSEED='42'
.venv-ml\Scripts\python.exe -m ml.dataset
.venv-ml\Scripts\python.exe -m ml.train --min-bairro-count 50
.venv-ml\Scripts\python.exe -m ml.run_tests
.venv-ml\Scripts\python.exe -m ml.report
```

A execução original usa o Python integrado do Codex, dependências da Etapa 1 em `.runtime` e de ML em `.runtime_ml`. O bootstrap de `src/ml/runtime.py` prefere `.runtime_ml` quando essa pasta existe. Num ambiente virtual limpo, remova essas pastas do caminho do projeto ou use uma cópia do repositório sem pastas de runtime locais; elas não são controladas por Git. Não misture duas versões de NumPy no mesmo processo. Os testes da Etapa 1 e da Etapa 2 são executados em processos separados para preservar seus ambientes e relatórios.

Dependências diretas estão fixadas em `requirements-ml.txt`; versões efetivamente importadas constam em `models/config_modelo.json`. TensorFlow/Keras foram escolhidos conforme a preferência da atividade. O treinamento usa os dispositivos realmente reconhecidos por TensorFlow, sem pressupor GPU. Referências consultadas em 09/11/2026:

- [Instalação oficial do TensorFlow](https://www.tensorflow.org/install/pip).
- [EarlyStopping — Keras](https://keras.io/api/callbacks/early_stopping/).
- [PyDataset — Keras](https://keras.io/api/utils/python_utils/#pydataset-class).
- [OneHotEncoder — scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder.html).

## Entradas necessárias

Na pasta `data/processed`, manter intactos `base_modelagem.parquet`, `metadados_modelagem.parquet`, `ocorrencias_elegiveis.parquet` e `esquema_modelagem.json`. Os oito testes originais também precisam dos demais processados, intermediários e dos três XLSX nos caminhos registrados nos manifestos da Etapa 1; uma mudança de caminho deve ser tratada com cuidado sem modificar os arquivos originais. A auditoria não é reexecutada para treinar.

O alinhamento é verificado por índice/chave e comparação com a base analítica. Qualquer divergência interrompe a execução antes do treinamento. A divisão é pelo ano da data do fato. Os testes fazem uma alteração apenas numa view em memória e verificam que ela provoca rejeição.

## Decisões fixadas antes do treino

- Atributos: `mes`, `dia_semana`, `tipo_local`, `bairro`; alvo separado. `periodo_fato` e demais campos não são passados ao codificador.
- Mês/dia recebem One-Hot nominal. Tipos de local e bairros são normalizados em NFC, espaços e maiúsculas, sem fuzzy matching.
- Foram revistas as categorias de 2023 e possíveis equivalências de acentuação. Somente a lista explícita de `ACCENT_ALIASES` é elegível, e um alias só é ativado se ambas as grafias aparecerem no treino. Não se fundem abreviações ou zonas distintas por suposição.
- Bairros sem letras são tratados como ausentes. Bairros com menos de 50 observações em 2023 usam um bucket estatístico de raros, que não afirma equivalência geográfica; o limiar é configurável, mas não foi otimizado nesta etapa.
- Bairro desconhecido usa o bucket de raros e tipo de local desconhecido usa a representação de ausente. As contagens de novos/ausentes são registradas separadamente para diagnóstico e não viram entradas extras.
- Vocabulários e frequências são ajustados só em 2023. A transformação de 2024 não ajusta nada. A ausência não remove observações.
- One-Hot CSR float32, densificação somente por lote de 256; não se materializa a matriz densa completa.
- Dense(64, ReLU) → Dense(1, sigmoid); BCE e Adam 0,001; 30 épocas máximas; EarlyStopping val_loss, paciência 5 e melhores pesos restaurados; semente 42; threshold fixo 0,5; sem balanceamento.

Não alterar limiar, atributos ou hiperparâmetros após consultar o desempenho desta execução. Experimentos posteriores exigem autorização da etapa correspondente e não devem abrir 2025. Se uma nova execução for solicitada, ela substituirá os artefatos da Etapa 2 nos mesmos caminhos; preserve a pasta antes se precisar comparar versões. O script nunca sobrescreve resultados da Etapa 1.

## Persistência e inferência

O arquivo `.keras` inclui arquitetura e pesos; a arquitetura também fica em JSON. `preprocessador.joblib` guarda os vocabulários, regras, frequências e proveniência do ajuste. Somente carregue artefatos locais confiáveis. Exemplo de interface Python:

```python
from ml.inference import ClassificadorOcorrencias

classificador = ClassificadorOcorrencias()
resultado = classificador.classificar(
    mes=5,
    dia_semana=2,       # segunda=0, quarta=2
    tipo_local='VIA PÚBLICA',
    bairro='BELA VISTA',
)
print(resultado)
```

Os quatro argumentos são obrigatórios, mas `None` é aceito para ausências; mês/dia inválidos, tipos errados e campos adicionais no pré-processador são rejeitados. A inferência retorna código/classe e probabilidades complementares de furto/roubo. Elas não foram calibradas nem representam risco de ocorrência futura. Campos desconhecidos usam as regras descritas acima; a aplicação futura deverá explicar essas limitações.

## Testes e evidências

`python -m ml.run_tests` executa os oito testes anteriores sem executar o bloco que grava `reports/testes_integridade.json`, preservando-o. A suíte nova cobre divisão, chaves, alinhamento, entradas permitidas, ajuste só no treino, desconhecidos, ausências, rótulos, recarga, inferência, integridade dos hashes e bloqueio de 2025. Logs e resultados ficam em `reports/etapa2/`. Falhas retornam código diferente de zero.

O treino compara todas as probabilidades da validação antes e depois de recarregar modelo e pré-processador (atol=1e-7, rtol=0). O manifesto `acesso_dados.json` registra anos usados; os testes confrontam-no com configuração, métricas e dimensões dos artefatos. O manifesto não é uma barreira de acesso fora do processo: a restrição é implementada e verificada nos pontos de carregamento e avaliação do pipeline.

## Correções durante a execução

Uma primeira sondagem ocorreu enquanto o pip ainda copiava pacotes para `.runtime_ml` e encontrou módulo ainda indisponível; foi refeita depois da instalação. A inspeção usou inicialmente a API antiga `fetch_arrow_table`; foi adaptada para `sql(...).to_arrow_table()`. A primeira tentativa de treino parou antes do ajuste porque havia um resultado DuckDB 2 ainda não consumido; as consultas de uma linha passaram a ser consumidas integralmente com `fetchall()`. Essas correções não mudaram dados, arquitetura nem hiperparâmetros. Erros do comando de treino ficam em `reports/etapa2/falhas_execucao.log`.

## Entrega

Resultados e análise A–I em `reports/relatorio_etapa2.md`, notebook executado em `notebooks/GS_Classificacao_MLP_Completo.ipynb`, modelo e pré-processador em `models/`. O notebook consolidado lê agregados e código-fonte; não executa treinamento ou inferência automaticamente. O exemplo de recarga do baseline é preservado como resultado histórico. Para abrir em Jupyter, instale Jupyter no ambiente de ML, caso necessário.

Arquivos binários de modelo, pré-processador, runtimes e previsões individuais de validação ficam ignorados pelo Git. A documentação, o código, os agregados, os gráficos e as configurações podem integrar a entrega acadêmica. Não publique dados brutos, bases volumosas ou identificadores de boletins. Esta etapa termina após a primeira MLP; não inclui experimentos sistemáticos ou desenvolvimento web.


## Navegação atual — 11/11/2026

O notebook único consolida as cinco etapas e não executa inferência ou treinamento automaticamente. Os comandos acima são históricos: para reprodução, use uma cópia histórica separada conforme o notebook. Os resultados originais permanecem nos relatórios. Consulte [o mapa de consolidação](consolidacao_academica.md).
