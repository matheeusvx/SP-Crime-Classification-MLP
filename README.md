# Global Solution FIAP — classificação de celulares subtraídos em São Paulo

Projeto acadêmico FIAP 2026.2. Etapas 1 a 5 concluídas; **Etapa 5.6: correções pós-auditoria**. Modelo final `gs-celulares-sp-dense64-v1.0.0`, Dense64 (299→64→1; 19.265 parâmetros), quatro entradas: mês, dia da semana, tipo de local e bairro. Rótulos: **0=FURTO; 1=ROUBO**. Não utiliza `periodo_fato`.

Classifica características de registros históricos de celulares subtraídos da capital, não todas as ocorrências criminais. Não prevê crimes futuros, não determina classificação jurídica e não foi validado para decisões policiais reais. Não é sistema oficial. Nenhuma aplicação web/API/dashboard foi implementada.

## Estado e resultados históricos

Treino: 2023 (190.124 BOs); validação: 2024 (158.895); teste final: 2025 (156.168). Dense64 B64_full_s42, Adam 0,001, batch 256, três épocas, seed 42, limiar 0,5, sem calibrador. Pesos, pré-processador, manifesto e resultados permanecem congelados.

2025: Accuracy 68,82%; Macro F1 67,09%; precision/recall de roubo 56,15%/63,42%; balanced accuracy 67,65%; Brier 0,20055; Log Loss 0,58351; ECE10 8,10%. A auditoria reproduziu esses resultados.

A rede supera a classe majoritária, mas **não demonstrou ganho consistente sobre uma referência retrospectiva por frequências** (Accuracy 69,28%, Macro F1 67,27%, AUC 0,7389; AUC da MLP 0,7412). Essa comparação foi construída depois do teste, não é experimento independente nem substitui a seleção histórica.

A rejeição de Platt no limiar 0,5 confundiu qualidade probabilística e ponto de operação. A revisão corrige a interpretação, não adota calibração: scores sigmoid continuam não calibrados e superestimaram em média roubo em cerca de 8 pp em 2025. Detalhes na errata e nas limitações.

**Teste consumido:** estatísticas de 2025 foram examinadas na Etapa 1, o ano foi avaliado na Etapa 5 e novamente consultado na auditoria. Não serve como teste independente para uma v2 desenvolvida após esses diagnósticos. Nova versão exige protocolo definido antes dos resultados e novo teste, por exemplo 2026 se disponível e de qualidade adequada. Não remover controles/cache nem reabrir o ano para escolher configurações.

## Integração Python recomendada

Instalar dependências de `requirements-final.txt` em ambiente Python 3.12 e definir `PYTHONPATH=src`. Os artefatos binários aprovados permanecem locais, fora do Git; conferir os hashes no manifesto antes de usá-los.

```python
from final5.validation import SafeClassifier

classificador = SafeClassifier()
opcoes = classificador.validator.vocabulary()
resultado = classificador.classify({
    'mes': 5, 'dia_semana': 2,
    'tipo_local': 'VIA PÚBLICA', 'bairro': 'BELA VISTA',
})
```

Contrato seguro **1.1.0**: mês e dia obrigatórios (segunda=0); campos categóricos controlados; desconhecidos rejeitados sem inferência. Local/bairro None são ausência explícita com aviso; bairro raro conhecido é aceito com aviso. Sem unificar globalmente acentos de bairro. O retorno traz classe, scores sigmoid não calibrados, versões e avisos/erros. Ver [contrato seguro](docs/contrato_inferencia_seguro.md).

`src/ml/inference.py` é legado do baseline da Etapa 2. `final5.pipeline.FinalPipeline` conserva o comportamento histórico congelado e deve ser usado por novas integrações somente através do adaptador seguro. Não mover as classes referenciadas pelos arquivos joblib.

## Materiais

- [Auditoria independente](reports/auditoria_claude.md) e [oito correções pós-auditoria](reports/relatorio_correcoes_pos_auditoria.md).
- [Relatório final com errata](reports/relatorio_etapa5.md), [notebook acadêmico](notebooks/05_avaliacao_final.ipynb) e [decisão revisada](docs/decisao_modelo_final.md).
- [Limitações e vieses](docs/limitacoes_modelo_final.md), [versionamento](docs/versionamento.md) e [preparação da Etapa 6](docs/recomendacoes_etapa6.md).
- Histórico preservado: relatórios e notebooks das Etapas 1–4; [engenharia de dados](reports/relatorio_etapa1.md), [decisões de origem](docs/decisoes.md), `src/data`, `src/ml`, `src/diagnostics`, `src/experiments4` e `src/final5`.

## Regressão de manutenção

Em PowerShell, com o ambiente completo do projeto e `requirements-ml.txt`:

```powershell
$env:PYTHONPATH='src'
python -m maintenance56.run_tests
```

O runner grava apenas logs/resultados em `reports/pos_auditoria`. Preserva os 83 testes históricos; executa os 75 anteriores ao teste final e os testes novos de contrato. As oito verificações FinalPost de cache de 2025 ficam separadas e não são executadas nesta manutenção. Testes estruturais históricos podem consultar metadados/rótulos de 2025; não treinam nem geram previsões ou novas comparações desse ano. Não executar runners históricos que regeneram treinamentos/relatórios para testar o novo contrato.

A inferência segura usa somente os artefatos e vocabulários, sem XLSX, Parquet ou rótulos. Os scripts de auditoria histórica requerem datasets locais e originais `D:/CelularesSubtraidos_2023.xlsx`, `2024.xlsx`, `2025.xlsx` com os nomes completos registrados na Etapa 1. Nenhuma ingestão/reconstrução é necessária para usar o classificador.

## Versionamento e dados

Git próprio inicializado **após a auditoria**, sem remoto/publicação. Snapshot `665d37b`, tag `snapshot-pos-auditoria-antes-correcoes`; não é prova retroativa do congelamento. Modelo v1.0.0 permanece o mesmo; revisão de software `pos-auditoria-1.0.0`, contrato 1.1.0. Manifestos antigos não foram reescritos; revisões de documentação/testes têm hashes antes/depois e original no snapshot.

Não versionar XLSX, Parquet, dados pessoais, previsões individuais, binários de modelo, caches, ambientes ou temporários. Dados ficam locais em `data/`, binários em `models/`, previsões privadas em diretórios ignorados. Somente agregados revisados e código/documentação integram os commits locais. Mais detalhes em `docs/versionamento.md`.
