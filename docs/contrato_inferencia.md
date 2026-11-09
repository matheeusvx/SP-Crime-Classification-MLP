# Contrato de inferência — gs-celulares-sp-dense64-v1.0.0

Interface Python reutilizável, sem HTTP, frontend ou dashboard. Depende apenas dos artefatos finais e do código cujos hashes constam no manifesto, sem ler bases de treinamento ou teste.

```python
from final5.pipeline import FinalPipeline

classificador = FinalPipeline()  # carregar uma vez por processo
resultado = classificador.classificar(
    mes=5,
    dia_semana=2,  # segunda=0, quarta=2
    tipo_local='VIA PÚBLICA',
    bairro='BELA VISTA',
)
```

Os quatro argumentos são obrigatórios, na ordem mês, dia da semana, tipo de local, bairro. Seus valores podem ser `None` conforme o contrato treinado. Não aceitar rubrica, natureza, ano, hora, período, chave ou dados pessoais como entradas extras.

| Campo | Domínio aceito | Ausência |
| --- | --- | --- |
| `mes` | inteiro 1–12, sem booleanos, strings numéricas ou floats | `None` com aviso de falta de exemplos de ausência no treino |
| `dia_semana` | inteiro 0–6; segunda=0 e domingo=6 | `None` com o mesmo aviso |
| `tipo_local` | texto, normalizado pelo pré-processador original | None/vazio/NULL/NAN/N/A representam ausência; categoria nova usa ausência com aviso |
| `bairro` | texto, com aliases ativos no treinamento e limiar50 | ausente recebe categoria própria; raro/novo usa bucket raro com aviso |

NFC, espaços e maiúsculas são tratados pelo objeto salvo. Aliases de local só reconhecem equivalência unívoca de acentuação a nome observado no treino; `VIA PUBLICA` e `VIA PÚBLICA` coincidem. `OUTROS` não é convertido em ausente. Bairro `BRÁS` e `BRAS` coincidem pelo alias existente. Não há fuzzy matching, expansão automática de abreviações ou geocodificação. O texto de bairro sem letras, como `'152'`, mantém a regra original de conversão em ausente, agora com aviso explícito; o número tipado `152` é rejeitado.

Mês/dia inválidos, NaN/inf, tipos incompatíveis e campos extras provocam `ValueError` ou `TypeError`, sem classificação silenciosa. Ausência tecnicamente aceita não significa que o comportamento esteja validado fora do suporte. Os avisos devem ser preservados na futura integração.

Retorno serializável:

```text
classe_estimada: FURTO ou ROUBO
codigo_classe: 0 ou 1
probabilidade_furto: float entre 0 e 1
probabilidade_roubo: float entre 0 e 1
versao_modelo: gs-celulares-sp-dense64-v1.0.0
probabilidades_calibradas: booleano conforme manifesto
avisos: lista de objetos {campo, codigo, mensagem}
```

As probabilidades somam1 e o limiar permanece0,5. A decisão de calibração e sua evidência estão em `reports/etapa5/decisao_calibracao.json`; não deduzir calibração apenas porque há uma sigmoid. Não chamar uma dessas probabilidades de chance de um crime futuro acontecer.

O carregamento confere o manifesto e os hashes antes de desserializar os artefatos locais. Manter os caminhos relativos listados no manifesto ao distribuir o projeto. O objeto pré-processador usa a classe de `src/experiments4/preprocessing.py`, preservada; não reimplementar sua lógica no frontend.

Para usar no ambiente de ML já configurado, definir `PYTHONPATH=src`. Para inferência, as versões fixadas em `requirements-final.txt` são suficientes; para auditoria/reprodução da avaliação, manter também o ambiente completo de `requirements-ml.txt`. A inicialização deve falhar se os hashes, versão ou dimensões forem incompatíveis.

Uso previsto: demonstração acadêmica sobre registros históricos de celulares subtraídos em São Paulo capital. A resposta não constitui determinação jurídica, não prevê criminalidade futura, não é um sistema oficial e não foi validada para decisão policial ou operacional real.
