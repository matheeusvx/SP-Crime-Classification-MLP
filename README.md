# Global Solution FIAP — Segurança Pública Inteligente em São Paulo

Etapa 1: auditoria, engenharia de dados e preparação para classificação de ocorrências **FURTO=0 / ROUBO=1**. Nenhum modelo ou aplicação web foi implementado. O universo é o extrato SSP-SP de boletins envolvendo celulares subtraídos, limitado ao município do fato em São Paulo capital. Não é um sistema de previsão de crimes futuros.

## Entrega

- [Relatório completo e síntese A–H](reports/relatorio_etapa1.md): resultados, qualidade, decisões, cenários, limitações e pendências.
- [Notebook executado](notebooks/01_auditoria_exploracao.ipynb): análise em português, consumindo agregados.
- [Decisões e proveniência](docs/decisoes.md).
- `reports/tables/`: inventário de campos, dicionário, comparação dos esquemas, classes, geografia, qualidade e amostragem.
- `data/processed/`: bases Parquet e esquema explícito de entradas, sempre locais e ignoradas pelo Git.

## Reprodução

Python 3.12 recomendado. Em um terminal PowerShell, na raiz do projeto:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe src/data/run.py --input-dir 'D:\'
```

A pasta de entrada deve conter os arquivos originais, com os nomes fornecidos:

```text
CelularesSubtraidos_2023.xlsx
CelularesSubtraidos_2024.xlsx
CelularesSubtraidos_2025.xlsx
```

Use `--input-dir 'C:\caminho\dos\arquivos'` em outro computador. O pipeline descobre as abas pelos relacionamentos OOXML e cabeçalhos, não pelo nome da aba. O cache de conversão é validado pelo SHA256 do original; `--force` refaz os intermediários. Auditoria, consolidação, testes e relatório são refeitos sobre esses intermediários. `--skip-ingest` pressupõe intermediários íntegros e ainda requer os originais para documentação e testes de conservação.

O notebook não depende de carregar os XLSX; execute suas células após gerar os relatórios. Para abri-lo em Jupyter, instale `jupyterlab` separadamente no ambiente de sua preferência. Ele já contém saídas executadas e referencia a figura local.

Para rodar só as verificações ou regenerar o relatório:

```powershell
.venv\Scripts\python.exe tests/test_integridade.py
.venv\Scripts\python.exe src/data/report.py
```

Na execução original, o Python disponível era o runtime integrado do Codex. As dependências foram instaladas na pasta local `.runtime/`, ignorada pelo Git; os scripts também funcionam com o ambiente virtual acima. O limite de 1,5 GB aplica-se ao DuckDB, não ao processo inteiro. Reserve espaço em disco para aproximadamente 400 MB de originais, intermediários, saídas e temporários que podem ocupar alguns GB. As dependências também ocupam disco. Não é preciso GPU.

## Fluxo e segurança dos dados

1. `ingest.py`: originais intactos → Parquet em lotes de 20 mil linhas, com lexemas preservados.
2. `source_metadata.py` e `audit.py`: metodologia, dicionário, perfis, frequências, geografia e datas, antes dos filtros.
3. `prepare.py`: consenso por boletim, recorte geográfico/temporal, regras de rótulo, quarentena, base analítica, entradas da MLP e amostra proporcional de 20 mil BOs.
4. `test_integridade.py`: invariantes e confronto com todas as linhas de origem dos BOs elegíveis; falhas interrompem a execução.
5. `report.py`: tabelas, figura, notebook executado e síntese A–H impressa no terminal.

Somente os cinco campos listados em `data/processed/esquema_modelagem.json` podem ser usados como entradas candidatas. O alvo deve ser separado. Hora e período brutos ficam somente na base analítica; o modelo recebe o período harmonizado, cuja convenção está documentada. Metadados não são preditores e ficam alinhados por índice de linha à base ordenada por chave; não reordene um arquivo sem aplicar a mesma permutação ao outro. A base analítica e a amostra contêm metadados técnicos e não devem ser passadas integralmente a um estimador.

Não há imputação, codificador, escalonador ajustado ou divisão definitiva. A proposta de divisão temporal e as escolhas pendentes precisam de avaliação antes da Etapa 2. O conjunto de teste futuro não deve orientar decisões de modelagem.

Não envie os XLSX, intermediários, bases processadas ou chaves técnicas para GitHub ou serviços externos. A `.gitignore` exclui esses arquivos. Relatórios contêm apenas agregados e categorias públicas, sem exemplos de boletins, endereços ou coordenadas. Este diretório não estava inicializado como repositório Git e nenhum commit ou envio remoto foi feito.
