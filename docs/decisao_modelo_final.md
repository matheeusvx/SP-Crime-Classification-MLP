# Decisão do modelo final

Modelo selecionado pelo usuário antes do teste: **B64_full_s42 / Dense64**, versão **gs-celulares-sp-dense64-v1.0.0**. Esta documentação consolida as decisões do manifesto, sem alterar os artefatos avaliados.

- Origem: `models/experiments/etapa4/B64_full_s42/`, modelo e pré-processador byte a byte idênticos às cópias em `models/final/`.
- Entradas: mês, dia da semana, tipo de local e bairro; 299 colunas One-Hot, Dense64 ReLU e sigmoid, 19.265 parâmetros. Adam0,001, BCE, batch256, três épocas, semente42. Sem dropout ou L2.
- Motivo: desempenho semelhante entre alternativas, estabilidade em três sementes e simplicidade relativa. Dense32 permanece alternativa compacta;64→32 teve maior recall e mais FP. Nenhuma alternativa foi comparada em2025.
- Pré-processador: o objeto experimental original, escopo completo2023, 190.124 registros, frequência mínima50 e alias unívoco de acentuação de local. Não há novo ajuste de vocabulário ou pesos.
- Calibração: **rejeitada antes do teste**. Platt melhorou Brier/Log Loss no holdout2024, mas recall de roubo caiu de 63.32% para 59.84%, além do limite de1pp previamente registrado. Não foi criado calibrador.joblib final. Threshold0,5 e sigmoid original mantidos.
- Congelamento: **2026-11-09T19:42:06.159595-03:00**, horário de São Paulo; registro UTC original em `models/final/manifesto.json`. SHA256 do manifesto: `b992412335c69623bdf63c9341cefaa82e0a81ae73d7d32e110f2498faa8c532`.
- Inferência2025 iniciada somente em `2026-11-09T22:46:16.220635+00:00` UTC, após75 testes prévios. O registro de avaliação tem uma chamada de inferência em lotes e impede repetição silenciosa. Não houve ajuste após o teste.

Limitações: domínio de celulares subtraídos da capital; contexto ambíguo; possíveis efeitos administrativos; mudança de distribuição; saída não calibrada; ausência temporal sem exemplos no treino; bucket compartilhado entre raros e novos. Não determina juridicamente roubo/furto, não prevê crimes futuros, não é sistema oficial e não foi validado para decisões policiais/operacionais reais.


## Errata pós-auditoria — 09/11/2026

A decisão histórica de não adoção foi cumprida, mas a justificativa de recall acima não mede exclusivamente qualidade probabilística. Platt Scaling monotônico preserva ordenação; o limiar 0,5 calibrado correspondia a aproximadamente 0,5218 na escala original. A redução de recall de 3,49 pp é efeito de mudança do ponto de operação, não evidência isolada de piora da calibração. No holdout 2024 melhoraram Brier (0,200356→0,199286), Log Loss (0,583488→0,581087) e ECE10 (3,81%→2,29%). Calibração mede correspondência entre scores e frequências; ponto de operação transforma scores em classes. Essas decisões precisam ser separadas em protocolo futuro.

A v1.0.0 mantém sigmoid original não calibrada e limiar 0,5; nenhum calibrador foi adotado nesta revisão. Em 2025 houve superestimação média de roubo de aproximadamente 8,10 pp (44,31% previsto, 36,22% observado), com discriminação semelhante à de 2024 segundo a auditoria. Não se recalibrou nem se ajustou o modelo após o teste.

A comparação retrospectiva por frequências encontrou Accuracy 69,28%, Macro F1 67,27%, AUC 0,7389, contra 68,82%, 67,09%, 0,7412 da MLP. Não há ganho consistente demonstrado da rede além da classe majoritária. A tabela não constitui experimento independente nem motivo para substituir o modelo selecionado.

A seleção Dense64 continua histórica. O congelamento é consistente com os arquivos, mas os timestamps/hashes originais são autoatestados; o Git próprio foi criado somente na Etapa 5.6. A auditoria reabriu 2025, também explorado estatisticamente na Etapa 1. Ele não é teste novo para futuras versões. Ver `limitacoes_modelo_final.md`, `versionamento.md` e `contrato_inferencia_seguro.md`.
