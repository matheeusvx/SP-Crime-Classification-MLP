# Contrato seguro de inferência — revisão 1.1.0

Revisão de software pós-auditoria, sem novo treinamento. Modelo **gs-celulares-sp-dense64-v1.0.0**, pré-processador original, limiar **0,5**, sigmoid **não calibrada**. Este contrato substitui, para novas integrações, as permissões inseguras do contrato histórico da Etapa 5; não reescreve `models/final/contrato.json`.

## Interface recomendada

Com as dependências de `requirements-final.txt` instaladas e `PYTHONPATH=src`:

```python
from final5.validation import SafeClassifier

classificador = SafeClassifier()  # carregar uma vez por processo
opcoes = classificador.validator.vocabulary()
resultado = classificador.classify({
    'mes': 5, 'dia_semana': 2,
    'tipo_local': 'VIA PÚBLICA', 'bairro': 'BELA VISTA',
})
assert resultado['status'] == 'ok'
```

Não usar `ml.inference.ClassificadorOcorrencias` (baseline histórico) nem chamar diretamente `final5.pipeline.FinalPipeline` na futura interface: este último preserva permissões históricas para reprodução, não o contrato seguro.

## Campos controlados

Exatamente quatro chaves, sem atributos extras. Campo omitido é erro de esquema.

| Campo | Opções e validação |
| --- | --- |
| `mes` | Inteiro 1–12 obrigatório. Rejeitar None, booleanos, floats, strings numéricas, NaN e infinito. |
| `dia_semana` | Inteiro 0–6 obrigatório; segunda=0, terça=1, quarta=2, quinta=3, sexta=4, sábado=5, domingo=6. Mesmas rejeições de tipo. |
| `tipo_local` | Seleção de categoria conhecida do pré-processador de 2023, ou opção explícita de ausência (`None`). Desconhecido é erro, nunca convertido em ausência. |
| `bairro` | Seleção de categoria conhecida em 2023, frequente ou rara, ou ausência explícita (`None`). Nome desconhecido é erro; pedir escolha explícita, sem fuzzy matching. Números, texto sem letras, vazios e sentinelas textuais são erros. |

`vocabulary()` deriva as opções apenas de `preprocessor.known`, sem datasets. Retorna meses, dias, locais conhecidos e bairros com `grupo=frequente/raro`; a lista é o vocabulário de treinamento, não um cadastro oficial. O bucket raro não é uma opção selecionável. Não inserir sentinelas `__AUSENTE__`/`__BAIRRO_RARO__`. O frontend futuro deve enviar os valores fornecidos pelo backend e incluir uma escolha explícita “não informado” somente para local/bairro. Não expandir automaticamente o vocabulário com dados da aplicação.

Caixa, espaços, NFC e aliases já existentes são processados pelo próprio objeto congelado. `VIA PUBLICA`/`VIA PÚBLICA` coincidem; `BRAS`/`BRÁS` usam o alias verificado. Isso não autoriza remover todos os acentos de bairros: `JARDIM ANGELA` e `JARDIM ÂNGELA` permanecem categorias distintas. A camada preserva essa limitação e exige seleção explícita; não resolve semanticamente grafias equivalentes. `OUTROS` continua separado de ausência.

## Respostas

Sucesso (os dois valores `s` são números retornados pelo modelo, não constantes de exemplo):

```text
{
  status: "ok",
  classe_estimada: "FURTO" ou "ROUBO", codigo_classe: 0 ou 1,
  scores_sigmoid: {furto: 1-s, roubo: s},
  versao_modelo: "gs-celulares-sp-dense64-v1.0.0",
  versao_contrato: "1.1.0", probabilidades_calibradas: false,
  avisos: [...], erros: [], grupos: {tipo_local: ..., bairro: ...},
  interpretacao_scores: "Estimativas não calibradas de classificação; não são chance de crime futuro."
}
```

Scores finitos entre 0 e 1, soma aproximadamente 1; ROUBO se score ≥0,5. A saída preserva o nome histórico `probabilidades_calibradas` como metadado, mas expõe os valores como **scores sigmoid não calibrados**. Se exibidos futuramente, não usar “chance de crime” ou “risco do bairro”.

Exemplo inválido: `{'mes': None, 'dia_semana': 2, 'tipo_local': 'PRAIA', 'bairro': '123'}`.

```json
{
  "status": "erro_validacao",
  "versao_modelo": "gs-celulares-sp-dense64-v1.0.0",
  "versao_contrato": "1.1.0",
  "probabilidades_calibradas": false,
  "erros": [
    {"campo": "mes", "codigo": "dominio_invalido", "mensagem": "mes: selecione um inteiro de 1 a 12, não nulo."},
    {"campo": "tipo_local", "codigo": "categoria_desconhecida", "mensagem": "Categoria não reconhecida. Escolha explicitamente uma opção do vocabulário."},
    {"campo": "bairro", "codigo": "categoria_invalida", "mensagem": "Selecione uma categoria reconhecida ou ausência explícita (None)."}
  ],
  "avisos": [], "grupos": {"tipo_local": "desconhecido"}
}
```

Erros não contêm classe nem scores e não chamam a rede. Ausência explícita de local/bairro e bairro raro reconhecido são aceitos com avisos; mês/dia ausentes sempre bloqueados. `vocabulary()['bairro']` permite selecionar um raro; a resposta registra `grupos.bairro='raro'` e aviso `bairro_raro`. Não apresentar a saída desses grupos como robustez comprovada.

Falhas de integridade/carregamento são erros técnicos que impedem a inicialização, não erros de formulário nem respostas de classificação. O adaptador verifica o manifesto e fixa seu SHA-256 aprovado; carrega apenas artefatos locais confiáveis. Não aceitar upload de modelos/joblib.

## Prontidão

Contrato Python e validação cobertos por regressão; não há API HTTP, autenticação, interface, dashboard ou implantação. A integração futura deve reutilizar este adaptador, exibir limitações e preservar avisos. Sem acesso aos datasets na inferência. Ver `limitacoes_modelo_final.md` e `recomendacoes_etapa6.md`.
