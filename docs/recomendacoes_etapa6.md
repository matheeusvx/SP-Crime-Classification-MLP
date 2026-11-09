# Integração futura — Etapa 6, ainda não implementada

1. Carregar `FinalPipeline` uma vez por processo e reutilizá-lo, sem executar treinamentos ou scripts de avaliação na inicialização. Os artefatos de `models/final` e os arquivos de código listados no manifesto compõem uma única versão.
2. Enviar apenas mês, dia da semana, tipo de local e bairro. Seguir o domínio e a ordem de `docs/contrato_inferencia.md`; não fornecer natureza, rubrica, ano, período, hora ou identificadores. Confirmar segunda=0 no formulário futuro.
3. Validar tipos e domínios antes da chamada e tratar `ValueError`/`TypeError` como erro de entrada. Não converter automaticamente qualquer valor inválido em uma categoria aceitável. Preservar os avisos estruturados sobre ausências, raros e desconhecidos.
4. Usar o pré-processador salvo no backend; não duplicar aliases ou One-Hot em JavaScript. O tamanho299 e a ordem das colunas são do artefato, não valores a inferir a partir da entrada do usuário.
5. Apresentar classe estimada e probabilidades estimadas com a indicação efetiva de calibração. Explicar que o classificador descreve compatibilidade entre características e classes; não prevê se um crime acontecerá, não determina natureza jurídica e não mede segurança de bairros.
6. Mostrar as limitações do domínio: celulares subtraídos da capital, registros históricos, contextos ambíguos, possíveis efeitos administrativos de preenchimento e mudança de distribuição. Destinação acadêmica, sem validação para operação policial.
7. Não incluir acesso a XLSX, Parquet ou previsões individuais no serviço de inferência. Dados pessoais não são entradas do modelo. Para diagnóstico de uso futuro, registrar somente contagens agregadas de avisos/erros e a versão do pipeline, conforme necessidade justificada.
8. Verificar hashes no deploy e executar testes de contrato, exemplos válidos/ausentes/novos e falhas de inicialização. Não permitir envio de modelos ou arquivos joblib pelo usuário final. O pacote é fornecido localmente como artefato do projeto.
9. Documentar os resultados finais de2025 como avaliação encerrada. Não usar esse conjunto para ajustar o modelo na aplicação nem prometer o mesmo desempenho em outra população. Nova versão exige protocolo de desenvolvimento e avaliação próprios.
10. Manter o modelo, threshold e eventual calibrador exatamente como congelados. Uma alteração futura cria nova versão, não substitui silenciosamente o modelo avaliado.

Nenhum frontend, endpoint HTTP ou dashboard foi criado nesta etapa. A implementação web depende de autorização específica para a Etapa6.
