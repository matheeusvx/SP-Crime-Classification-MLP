# Recomendações para a Etapa 5

Não há vencedor definitivo. Nenhum dado de 2025 foi avaliado nesta etapa. Há **ganho limitado**, e não evidência de que mais capacidade resolva a tarefa.

## Candidatas e evidências

- Principal experimental: **B64 / Dense64**, quatro atributos, limiar50, alias inequívoco de acentuação de local. Três épocas fixas escolhidas internamente. Média de três sementes: Macro F1=0.67710 (DP 0.00018), balanced accuracy=0.67716, recall roubo=0.62690. Diferença de Macro F1 contra histórico: -0.056 pp; não é ganho comprovado.
- Alternativa com prioridade em recall: **B64_32 / Dense64→32**, Macro F1=0.67590, recall=0.64851; mais FP e parâmetros. Só faz sentido se esse compromisso for aceito; profundidade não produziu melhoria geral.
- Alternativa compacta: **B32**, 9.633 parâmetros. Macro F1 de uma semente completa ~0,67745, próximo dos demais. Não se pode afirmar superioridade ou estabilidade com uma semente; sua simplicidade merece consideração, sem acrescentar tentativas nesta etapa após ver 2024.
- Preservar o baseline histórico como opção de referência: Macro F1 0,67766, com EarlyStopping em 2024. Seu protocolo difere e a vantagem numérica pequena não é comparação imparcial de otimização.

## Antes de abrir 2025

1. Fixar a configuração final e o tratamento de ausências/novos/acentuação. Não transformar OUTROS em ausente; a relação de local com coleta continua sem confirmação semântica externa. A ablação mostra dependência e troca de erros, não prova causalidade ou ausência de vazamento.
2. Revisar a robustez dos buckets raros: mesmo com quatro atributos e limiar50, raros/novos seguem com FPR alto. Não inferir risco de bairros. Mudanças de representação adicionais exigem protocolo de desenvolvimento explícito e não usar 2025.
3. Decidir o orçamento final sem ajustá-lo ao teste. O recorte Jan–Set vs Q4 contém meses não observados no treino; três épocas foram uma escolha conservadora e podem limitar o reajuste. Não recomendar mais épocas apenas porque o histórico usou cinco e teve métrica ligeiramente maior.
4. Se calibrar ou escolher threshold, separar ajuste e verificação em dados de desenvolvimento; não usar os mesmos exemplos para afirmar melhoria imparcial. Os três epochs refits têm ECE/Brier que não superam consistentemente o histórico. Manter 0,5 até esse protocolo ser aprovado. Probabilidades não são risco futuro de crime.
5. Critérios finais: Macro F1 principal, balanced accuracy, recall/precision por classe, FP/FN, Brier/Log Loss, confiabilidade por suporte, grupos ausentes/raros/novos e custo. Não escolher pela melhor semente. Definir também os custos de FP/FN, hoje não fornecidos.
6. Após congelar modelo/pré-processador/threshold e protocolo de calibração, avaliar 2025 **uma única vez** para estimativa final. Não resolver empates nem refazer arquitetura com base nesse resultado. A Etapa 5 depende de autorização do usuário.

Artefatos por candidato: `reports/etapa4/candidatos_artefatos.json`. Todos os checkpoints e preprocessadores estão em `models/experiments/etapa4/`, sem promover qualquer arquivo a `mlp_baseline.keras`.
