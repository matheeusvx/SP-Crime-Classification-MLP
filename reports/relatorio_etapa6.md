# Etapa 6 — Plataforma web integrada à MLP

**Modelo:** `gs-celulares-sp-dense64-v1.0.0` (congelado). **Contrato:** seguro 1.1.0. **Estado:** aplicação funcional localmente; implantação pública preparada e não realizada.

Nenhum treinamento, calibração, alteração de limiar, nova inferência sobre 2025 ou experimento foi executado. Pesos, pré-processador e manifesto não foram modificados: a própria carga da API confere os hashes.

## 1. Decisões de implementação

| Decisão | Motivo |
| --- | --- |
| FastAPI usa `SafeClassifier`, carregado uma vez | Reutiliza a validação da Etapa 5.6; `FinalPipeline` não é chamado diretamente |
| Requisição Pydantic com campos `Any` e `extra='forbid'` | Tipos normais converteriam `"5"` em `5`, contornando o contrato |
| Erros de esquema respondidos pelo próprio contrato | Formato único e nenhuma regra duplicada |
| Falha de artefato mantém o processo ativo, com 503 | Erro explícito, nunca resposta fictícia |
| Lock em torno da inferência | Chamadas simultâneas ao Keras ficam serializadas; a latência é de milissegundos |
| Agregados JSON pré-computados | A aplicação não acessa Parquet nem planilhas |
| Métricas lidas de arquivos e tabelas existentes | Elimina transcrição manual; AUC e tabela de frequências vêm da auditoria |
| Texto de scores em decimais (0,745), não em porcentagem | Reduz a leitura como chance de crime |
| Frontend sem lógica de normalização | Grafias como `TATUAPE` e `TATUAPÉ` permanecem opções distintas |
| Resultado apagado quando a entrada muda | Evita associar um resultado a dados diferentes |
| FastAPI serve o build em produção | Mesma origem e implantação em um único contêiner |
| `README.md` e `.gitignore` raiz não alterados | A regressão confere seus hashes; a Etapa 6 usa `web/README.md` e `web/.gitignore` |

Tipos de local têm rótulo legível na tela (“Via Pública”), mas o valor enviado é o do vocabulário. Bairros aparecem como no vocabulário, pois a grafia distingue categorias. A busca sem acentos só filtra a lista.

## 2. Funcionalidades

- **Classificador:** quatro campos, bairro em lista pesquisável com “Não informado” explícito, exemplo identificado como hipotético, classe, dois scores não calibrados, explicação obrigatória, versões e avisos.
- **Painel histórico:** indicadores, evolução anual, série mensal de 36 meses, proporção de classes e tipo de local, com filtros de ano e tipo, tabelas alternativas e ressalvas. Não há dados de bairro nem rankings territoriais.
- **Sobre o modelo:** arquitetura 299 → 64 → 1, explicação em camadas, validação 2024 × teste 2025, matriz de confusão, três arquiteturas e referências simples.
- **Estados:** carregamento, sucesso, validação, comunicação, limite excedido e serviço indisponível.

`OUTROS` e “Não informado” recebem ressalva na tela. A nota sobre `OUTROS` e local ausente no resultado é de apresentação; o corpo de `/api/classify` segue integralmente o contrato. No gráfico por local, tipos com menos de 1.000 boletins nos três anos são somados em “Demais categorias”, o que também evita células muito pequenas nos filtros.

### Remodelação visual

A interface foi refeita com cartões, indicadores em destaque e visualizações inspiradas nas referências enviadas. Cada elemento usa dados reais:

| Elemento | Dados |
| --- | --- |
| Medidor semicircular e comparação furto × roubo | Scores da própria classificação, com a marca superior no limiar 0,5 |
| Comparar cenários | Classificações feitas pelo visitante, mantidas só em memória; selecionar uma restaura os campos sem nova chamada |
| Barras com destaque de mês e dia | Contagens históricas, atualizadas ao selecionar os campos |
| Acurácia publicada em grupos semelhantes | `reports/etapa5/metricas_grupos_2025.csv`, sem novo cálculo |
| Anel em espiral da distribuição das classes | Totais de furtos e roubos do período; adaptado do componente de referência enviado, sem `animejs`, ocultação de fatias nem dados de exemplo |
| Cilindros da evolução anual | Contagens de furtos e roubos por ano; adaptados do componente de referência enviado, sem `animejs` nem dados de exemplo. Altura do líquido proporcional ao valor, a partir de zero |
| Mapa de calor mês × dia, série com área e minigráficos | Novos agregados `por_dia_mes` e séries mensais |
| Diagrama da rede, matriz 2024/2025 e seleção de arquiteturas | Manifesto e métricas publicadas |

**Decisão metodológica:** não foi criado mapa de score do modelo por mês e dia, nem análise automática de sensibilidade. Isso apresentaria scores como risco por período e funcionaria como explicação individual sem método validado, o que as regras da etapa proíbem. A variação de cor no painel representa volume de registros; a tela informa que isso não indica risco.

**Animações:** implementadas em CSS e React, sem biblioteca adicional. A skill `stageshow`, indicada no pedido, não foi encontrada nesta instalação nem no catálogo. Todas as animações respeitam a preferência de movimento reduzido, e os valores finais não dependem delas. Testes confirmam o estado final com animação ativa, sem avaliar a fluidez percebida.

## 3. Segurança

CORS por lista explícita (curinga recusado); apenas GET e POST; atributos extras recusados; corpo limitado a 2 KB; 60 classificações por minuto e por IP; cabeçalhos CSP, `nosniff` e `frame-ancestors`; documentação desativada em produção; sem rota de treino ou upload; respostas sem hashes, caminhos ou eco da entrada; entradas não vão para logs nem para retreinamento.

## 4. Testes executados

| Suíte | Resultado |
| --- | --- |
| Regressão da Etapa 5.6 (mesmas suítes de `maintenance56.run_tests`) | **105 executados, 0 falhas, 0 erros** |
| API (pytest, modelo real, entradas sintéticas) | **73 aprovados** |
| Componentes (Vitest + Testing Library) | **31 aprovados** |
| Integração em navegador real (Playwright + Edge; desktop 1280 px e mobile 375 px) | **21 aprovados, 1 pulado** |

A regressão foi executada por suíte, sem regravar `reports/pos_auditoria`; resultado em `etapa6/regressao_105.json`. Os oito testes `FinalPost` de cache de 2025 continuam separados e não foram executados. O teste pulado é o de teclado físico no perfil móvel; ele foi executado no perfil desktop.

A integração usa navegador → build → FastAPI → `SafeClassifier` → Dense64 e confere classe e scores exibidos contra a interface Python segura, com três entradas hipotéticas. Cobre também aviso de bairro raro, ausência explícita, rejeição pela API, falha de rede, 503, teclado, ausência de rolagem horizontal, erros de console e bloqueio de arquivos internos.

Além disso, foram verificados manualmente `instalar.cmd`, o modo de desenvolvimento com proxy do Vite e o layout da imagem em pasta limpa. Nos três caminhos, o exemplo-base retornou roubo = 0,25536, compatível com o valor 0,2554 da auditoria.

Durante a verificação encontrou-se um defeito: corpo com bytes inválidos em UTF-8 recebia resposta 400 fora do contrato. Foi corrigido e coberto por teste.

## 5. Desempenho (`etapa6/desempenho.json`)

Medições locais, em CPU, sem rede.

| Item | Valor |
| --- | ---: |
| Carga do modelo e inicialização | ≈ 4,8 s |
| Memória residente após 300 classificações | ≈ 343 MB |
| Classificação (mediana / p95) | ≈ 4,4 ms / 5,6 ms |
| JavaScript inicial (gzip) | ≈ 94 KB |
| CSS (gzip) | ≈ 7,5 KB |
| Fonte Inter, subconjunto latino | ≈ 48 KB |
| Página do painel com Recharts, sob demanda (gzip) | ≈ 115 KB |
| `/api/options` descomprimido | ≈ 87 KB |

## 6. Dados e reprodutibilidade

`web/backend/scripts/gerar_agregados.py` gera os JSON públicos de forma determinística, sem carregar o modelo. Os totais conferem com 505.187 boletins, 298.083 furtos e 207.104 roubos e com as tabelas da Etapa 1. As contagens por ano e tipo de local leem rótulos de 2025 de forma descritiva, como o enunciado solicita para o painel; essa leitura não ajusta nem avalia o modelo. Proveniência em `etapa6/proveniencia_agregados.json`.

## 7. Evidências visuais

`etapa6/capturas/`, nos perfis `desktop-` e `mobile-`: classificador vazio e com resultado, aviso de bairro raro, erro de rede, serviço indisponível, painel e página sobre o modelo.

## 8. Limitações e pendências

| Item | Estado |
| --- | --- |
| Link público exigido pela FIAP | **Pendente.** Requer hospedagem e autorização; guia em `docs/implantacao_etapa6.md` |
| Imagem Docker | **Não construída**: o Docker Desktop estava desligado. Layout equivalente validado em pasta limpa |
| `README.md` raiz | **Desatualizado**: ainda afirma não haver aplicação web. Alterá-lo exige nova revisão autorizada no registro de hashes |
| Conexões lentas | Sem teste com rede limitada; há tempo limite de 20 s, divisão de código e mensagem de erro |
| Acessibilidade | Teclado e semântica testados; sem auditoria automatizada completa nem teste com leitor de tela |
| Mobile | Viewport emulado no Edge; sem aparelho físico |
| Vocabulário de bairros | Vem do treinamento de 2023 e inclui entradas sem curadoria, como nomes fora da capital. Não é cadastro oficial; a seleção foi preservada conforme o contrato |
| Limite de requisições | Em memória e por processo, adequado a uma demonstração |

**Alteração solicitada pelo responsável:** o cartão de limitações da página Sobre, o alerta do classificador e a frase de rodapé sobre projeto acadêmico e não oficialidade foram removidos da interface, o que altera o requisito original 7.5 e a regra 15. Permanecem na tela os avisos de scores não calibrados, a ressalva de “OUTROS”, a comparação com referências e a identificação “Demonstração acadêmica” no cabeçalho.

As limitações metodológicas do modelo continuam válidas e documentadas em `docs/limitacoes_modelo_final.md`: scores não calibrados, ausência de vantagem demonstrada sobre a tabela de frequências, possíveis proxies administrativos, bairros raros, grafias históricas, vieses de seleção, restrição de domínio e ausência de validação para uso real.
