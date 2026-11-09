# Limitações da Dense64 v1.0.0 — revisão pós-auditoria

Base de evidências: `reports/auditoria_claude.md`, achados A1–A4, M1–M7 e B1–B8. Os números seguintes são os publicados pela auditoria; esta revisão não reabre 2025 para inferência ou experimentos. Não há vazamento de informação comprovado. Associações, proxies e vieses de seleção não devem receber automaticamente esse diagnóstico.

## Sinal preditivo e comparação

A rede supera a referência majoritária, mas **não demonstrou ganho consistente sobre a referência retrospectiva de frequências por local/bairro**. A tabela foi construída após a divulgação do teste, não é um vencedor independente. O sinal disponível parece limitado e dominado por duas entradas. O teto empírico de contextos observados usa os próprios rótulos e não é limite matemático universal nem desempenho atingível fora da amostra. Redes maiores não corrigem automaticamente falta de informação.

## Tipo de local e canal administrativo

A auditoria associa ausências e `OUTROS` ao canal da Delegacia Eletrônica e à transição do preenchimento no segundo trimestre de 2024: ausência de 7,96% para 0,04% e `OUTROS` de 0,07% para 7,5%. É evidência forte de recodificação/formulário e proxy administrativo plausível, sem comprovar derivação do rótulo ou causalidade criminal. A relação via pública × outros locais também contém sinal contextual legítimo.

Ressalva de leitura da própria auditoria: sua frase “apenas na Delegacia Eletrônica” não é válida universalmente para `OUTROS`; a tabela A3 inclui `OUTROS` no canal presencial em 2025 (0,9% dos furtos e 0,2% dos roubos). A associação é forte/predominante, não exclusividade absoluta. A mudança específica do formulário é interpretação da auditoria baseada nos cruzamentos, não verificação independente de versões oficiais do formulário nesta manutenção.

O grupo ausente/OUTROS reúne 11.969 boletins em 2025, acurácia de 91,65%; excluindo-o descritivamente, 66,92% contra 68,82% geral. A diferença de aproximadamente 1,9 pp é de composição, não efeito causal de retirar o atributo e retreinar. `OUTROS` tinha só 12 exemplos de treino. Desconhecido não equivale semanticamente a ausente: o novo contrato o bloqueia.

## Bairro e grafias

1.666 bairros distintos de treinamento compartilham uma coluna rara. A auditoria encontrou 11.118 registros de via pública + raro/desconhecido em 2025, todos previstos como ROUBO, com 4.601 falsos positivos (FPR 100% nesse recorte). É consequência da representação e dos dados, não erro de pesos ou indicador de risco territorial. O contrato distingue frequente, raro e desconhecido; este último é rejeitado na integração nova.

A normalização histórica não unifica todos os acentos/abreviações. Há categorias duplicadas por grafia e respostas diferentes. Não foram criadas equivalências novas; a seleção controlada reduz ambiguidade, mas não elimina a limitação do modelo. As opções derivadas de registros não são cadastro oficial e requerem curadoria de apresentação futura sem mudar valores enviados ao modelo.

## Seleção e cobertura

A filtragem conservadora excluiu boletins com outras naturezas associadas: cerca de **4,3% dos roubos e 1,1% dos furtos** na capital, conforme auditoria M6. Roubos com localização/apreensão de veículo são sub-representados. Não é erro de rótulo; delimita o universo da classificação.

Boletins podem ser registrados após o ano do fato. A auditoria informa 0,8% de fatos de 2023 e 1,06% de 2024 em arquivos de anos seguintes; fatos de 2025 registrados em 2026 não estão cobertos. Os conjuntos têm maturação diferente. Conflitos internos de local/bairro também podem virar ausência, que não significa sempre “não informado”. O recorte geográfico usa circunscrição municipal, com ruído residual já documentado.

## Probabilidades, incerteza e tempo

Saídas sigmoid não calibradas. Em 2025, média prevista de roubo ≈44,31% contra prevalência de 36,22%: superestimação de ≈8,10 pp. A auditoria mostra ECE10≈0,080964 igual ao desvio médio e superestimação em todos os bins, AUC 0,7448→0,7412 e inclinação de calibração 0,954→0,951. A evidência aponta principalmente desajuste de nível associado à mudança de prevalência, com discriminação semelhante; não uma deterioração expressiva de ordenação. Não prova ausência de outras mudanças condicionais nem estabilidade futura. Brier/Log Loss não isolam calibração.

O recall perdido por Platt no limiar numérico 0,5 mede mudança do ponto de operação, não prova piora probabilística. A decisão histórica e os artefatos ficam preservados; não há recalibração nesta etapa. Os intervalos históricos IID são condicionais ao pipeline e não incluem dependência temporal, seleção e variabilidade de treino. Não foram substituídos por novos intervalos. As três sementes variaram inicialização, mantendo ordem dos lotes em 42; a estabilidade não cobre todas as fontes estocásticas. A seleção temporal interna de 2023 não permite avaliar adequadamente meses out–dez sem exemplos de treino; manter mês não equivale a sazonalidade validada.

## Teste consumido e validade externa

2025 foi consultado estatisticamente na Etapa 1, usado na avaliação final da Etapa 5 e novamente na auditoria. Foi posterior e fora do ajuste dos pesos da v1.0.0, mas não era absolutamente cego em todo o projeto e não é teste independente para v2 ajustada após esses diagnósticos. Futuras hipóteses precisam de protocolo prévio e dados novos (por exemplo 2026, sujeitos a acesso, qualidade e maturação); nenhuma v2 foi iniciada.

O modelo foi treinado em históricos de **celulares subtraídos de São Paulo capital**, não todas as ocorrências criminais. Não prevê crimes futuros, não determina juridicamente furto/roubo, não mede segurança de bairros e não é sistema oficial. Contextos idênticos podem ter rótulos diferentes. Demonstração acadêmica, sem validação para decisões policiais ou operacionais reais; resultados variam com distribuição e práticas de registro.
