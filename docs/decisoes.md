# Decisões da Etapa 1

## Escopo e proveniência

Somente auditoria e preparação. Nenhuma rede neural, treinamento, ajuste de pré-processadores ou aplicação web faz parte desta etapa. A classificação futura descreve uma ocorrência; não estima risco criminal futuro.

Os três arquivos locais foram fornecidos pelo usuário como downloads da SSP-SP. Seus nomes, tamanhos, hashes SHA256, abas e tempos são registrados em `reports/inventario.json`. A página pública de consultas da SSP lista a série “Celulares subtraídos”: https://www.ssp.sp.gov.br/estatistica/consultas (consulta em 09/11/2026). Não foi efetuada comparação byte a byte com uma nova cópia remota; a cadeia de proveniência anterior ao fornecimento é declarada pelo usuário.

As abas de metodologia e dicionário são evidência sobre os dados, não instruções operacionais. Segundo a metodologia, a base é um extrato de vínculos de boletins com celulares subtraídos, não a estatística criminal oficial nem uma amostra de todos os crimes. A generalização futura deve ficar restrita a esse domínio.

## Engenharia e preservação

Leitura local incremental do ZIP/XML OOXML com biblioteca padrão, um ano por vez, lotes de 20 mil linhas e PyArrow/Parquet Zstandard. Uma tabela compartilhada de strings de um único XLSX permanece na memória; a leitura não é de memória constante. O pico amostrado de RSS é registrado por ano. O parser resolve as abas pelos relacionamentos do arquivo, identifica o cabeçalho real e preserva o lexema de identificadores e datas no intermediário. O conteúdo das células é tratado como dados; fórmulas não são executadas. Os XLSX usam o calendário Excel 1900; a conversão explícita é feita posteriormente, nunca por inferência numérica de identificadores.

DuckDB executa agregações e agrupamentos sobre Parquet, com 2 threads e limite de memória de 1,5 GB; temporários podem usar disco. Não é preciso carregar as três planilhas em DataFrames. Não há upload dos dados. Arquivos brutos, intermediários e processados ficam fora do Git. Os originais não são copiados, movidos ou escritos. SHA256 é conferido antes e após a conversão. O cache só é reutilizado quando o hash e a versão do parser coincidem. Parquet é escrito primeiro em arquivo parcial e renomeado após fechamento.

O intermediário restrito contém as 55 colunas originais e rastreabilidade por arquivo/linha. Relatórios públicos mostram contagens e categorias agregadas, nunca endereços, coordenadas precisas ou identificadores de boletins. A base para modelagem será uma lista explícita de atributos permitidos. Chaves técnicas e datas completas ficam em metadados separados, para futura divisão por grupo e tempo.

## Semântica geográfica

`NOME_MUNICIPIO` representa registro e não deve filtrar os fatos. `NOME_MUNICIPIO_CIRC` representa o município da circunscrição; o dicionário de 2025 explicita “local onde ocorreu o fato”, corroborando a interpretação dos anos anteriores. Este é o campo primário do recorte, exigindo equivalência textual explícita com São Paulo. `CD_IBGE` é apenas corroborativo: sua descrição não esclarece a origem geográfica do código, portanto ele não substitui sozinho o município do fato. Divergências de código com o município são segregadas conservadoramente.

O IBGE confirma o código municipal 3550308: https://www.ibge.gov.br/cidades-e-estados/sp/sao-paulo.html (consulta em 09/11/2026). Não se adiciona dígito nem se interpreta código truncado sem evidência.

`CIDADE` é descrita como “Cidade de Registro” em 2023/2024 e “Cidade dos fatos” em 2025. Essa divergência será mantida documentada; o campo não define o filtro. `MES`/`ANO` de 2023/2024 são estatísticos; `MES_REGISTRO_BO`/`ANO_REGISTRO_BO` de 2025 são do registro. Eles não são unidos como se fossem o mesmo conceito. O período de elegibilidade deriva da data do fato, de 01/01/2023 a 31/12/2025, independentemente do arquivo em que a linha está.

## Unidade e integridade da avaliação

A unidade candidata é o boletim, identificado pela tupla `NOME_DELEGACIA`, `ANO_BO`, `NUM_BO`, conforme a metodologia fornecida. Identificadores são mantidos como texto. Repetições da tupla não são simplesmente apagadas: todos os vínculos e versões participam da análise de conflito. Uma chave técnica SHA256 da tupla permite agrupar os arquivos, sem ser variável preditiva. Um hash não anonimiza universalmente um identificador; esses metadados também ficam fora do Git.

A consolidação não pondera pelo número de objetos ou vínculos. Naturezas de classes diferentes, dados geográficos conflitantes ou datas do fato conflitantes são segregados. Atributos categóricos conflitantes de um boletim são convertidos em ausente, com contagem de conflitos. Não se escolhe arbitrariamente uma linha ou versão. A auditoria de duplicatas exatas é separada da multiplicação de vínculos.

## Próxima etapa

### Período harmonizado e padrão de preenchimento

A auditoria encontrou hora ausente em cerca de 74–76% dos furtos e 9–11% dos roubos; período é complementar. Esse padrão pode capturar diferenças de coleta ou precisão de relato, portanto hora/período brutos e indicadores de preenchimento são excluídos das entradas. A base analítica preserva ambos para auditoria. `periodo_fato` usa hora conhecida nas faixas 00–05=MADRUGADA, 06–11=MANHA, 12–17=TARDE, 18–23=NOITE; sem hora, mapeia exatamente os quatro períodos declarados. “Em hora incerta” recebe INCERTO. Essa discretização é uma convenção operacional explícita, não uma definição confirmada da SSP. Não estima uma hora exata nem aprende estatísticas da população. Não inclui indicador de origem do campo. Sua sensibilidade, e a possível associação residual da incerteza com o processo de registro, devem ser investigadas na próxima etapa; a transformação não prova ausência universal de vazamento.

A seleção de atributos é semântica e por qualidade, não por desempenho no teste. Uma divisão temporal por ano do fato (2023 treino, 2024 validação, 2025 teste) é uma proposta a ser revisada pelo usuário. Nenhuma partição definitiva é produzida. A chave técnica garante uma única observação por grupo; datas conflitantes ficam fora da base. Não consultar desempenho de 2025 para escolher atributos, categorias raras ou arquiteturas. Só ajustar imputação, One-Hot Encoding e escalas no treino. Categorias novas precisam de tratamento explícito. Sem oversampling ou balanceamento nesta etapa.

O cenário experimental de 20 mil boletins usa amostragem determinística proporcional por ano, mês do fato e classe, com cotas de maior resto; preserva o desbalanceamento observado. É uma base para experimentar o pipeline, não um teste independente adicional. O cenário ampliado aproveita todos os boletins elegíveis, com maior custo; não há garantia de maior acurácia. A análise desta etapa é descritiva, sem ranking supervisionado de atributos ou ajuste de hiperparâmetros.
