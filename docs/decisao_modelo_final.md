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
