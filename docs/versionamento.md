# Versionamento e rastreabilidade

O repositório próprio de `GS-CNN` foi inicializado **após** a avaliação final e a auditoria, em 09/11/2026. O snapshot inicial é `665d37b`, tag `snapshot-pos-auditoria-antes-correcoes`. Ele não constitui evidência retroativa de versionamento, congelamento ou ordem temporal antes do teste. Não houve alteração no repositório da pasta pessoal, configuração global ou criação de remoto. Identidade técnica de commit aplicada por comando, sem atribuir autoria humana fictícia.

| Componente | Identificação |
| --- | --- |
| Código | Commits locais Git; revisão de manutenção `pos-auditoria-1.0.0` |
| Modelo neural | `gs-celulares-sp-dense64-v1.0.0`, SHA-256 do manifesto e pesos originais |
| Pré-processador | O objeto original de B64_full_s42, SHA-256 próprio; não reajustado |
| Contrato histórico | `models/final/contrato.json`, imutável e inseguro para novas integrações sem adaptador |
| Contrato seguro | `1.1.0`, `final5.validation`, documentado separadamente |
| Dados | Versões e hashes originais nos metadados/manifesto; dados locais fora do Git |
| Relatórios | Publicação original da Etapa 5 + errata datada 5.6 e relatório próprio, sem trocar métricas |

Nenhuma revisão de código/contrato significa nova arquitetura ou treinamento. Um futuro ajuste de pesos, normalização aprendida, vocabulário, calibrador ou limiar exige nova identificação e protocolo. Não mover a classe `experiments4.preprocessing.ExperimentalPreprocessor` referenciada por joblib.

## Preservação verificável

`reports/pos_auditoria/estado_anterior.json` (inventário local de 408 arquivos, incluindo datasets e binários excluídos do Git) registra o estado anterior. `revisoes_autorizadas.json` versiona caminhos, motivos e hashes antes/depois das alterações; `maintenance56.integrity.verify_history` exige que o hash antigo corresponda ao blob do snapshot e o atual à revisão registrada. Arquivos sem revisão devem manter o hash histórico. Manifestos antigos, resultados JSON/CSV e fontes congeladas não são reescritos.

Testes antigos que chamavam preservação byte a byte passaram a verificar ambos os estados através desse mecanismo; não recebem dispensa genérica de integridade. As funções históricas de preservação continuam intactas: comandos históricos completos podem acusar as erratas autorizadas, por isso não são o runner de manutenção. A regressão recomendada é `python -m maintenance56.run_tests`, sem regenerar relatórios/treinos antigos.

`revisao_git.json` documenta a lista inicial revisada: somente fontes, documentação, agregados, figuras e notebooks sem registros individuais, com varredura adicional de CPF/chaves comuns. A `.gitignore` agora exclui recursivamente datasets, binários de modelos, previsões individuais, logs, caches, temporários e segredos usuais. Os artefatos volumosos ficam locais e sua identidade é representada por hashes. Não há remoto nem publicação automática.

Antes de novos commits, revisar `git diff --cached`, tamanho e conteúdo, inclusive outputs de notebooks e categorias extraídas de registros. Scan automatizado não garante ausência universal de informação sensível. Para distribuição futura, fornecer os artefatos aprovados por canal separado, conferir SHA-256 e manter o código de desserialização original.

Os hashes locais e a tag protegem contra alterações acidentais/revisões não registradas; não são atestação externa inviolável. Evidências anteriores continuam autoatestadas, conforme auditoria M5.
