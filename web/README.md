# Plataforma web — Etapa 6

Interface React e API FastAPI em torno da MLP congelada `gs-celulares-sp-dense64-v1.0.0`. Toda classificação passa por `final5.validation.SafeClassifier` (contrato seguro 1.1.0). Demonstração acadêmica: não é sistema oficial da SSP-SP e não prevê crimes.

## Executar no Windows

Requisitos: Python 3.12 e Node 22 no PATH. Os artefatos locais em `models/final/` precisam estar presentes (não são versionados). Os comandos abaixo partem da raiz do projeto.

| Objetivo | Comando |
| --- | --- |
| Instalar dependências Python e JavaScript | `web\scripts\instalar.cmd` |
| Iniciar backend e frontend e abrir o navegador | `web\scripts\iniciar.cmd` |
| Iniciar somente o backend | `web\scripts\iniciar-backend.cmd` |
| Iniciar somente o frontend | `web\scripts\iniciar-frontend.cmd` |
| Executar testes de API, componentes e integração | `web\scripts\testar.cmd` |

Interface: <http://127.0.0.1:5173>. API: <http://127.0.0.1:8000>, com documentação em <http://127.0.0.1:8000/api/docs> quando `APP_ENV=development`. O Vite encaminha `/api` para a porta 8000. Os testes de integração usam a porta 8010 e o Microsoft Edge instalado no Windows (altere com `E2E_BROWSER_CHANNEL`).

Variáveis estão em [`backend/.env.example`](backend/.env.example) e [`frontend/.env.example`](frontend/.env.example). Implantação: [`docs/implantacao_etapa6.md`](../docs/implantacao_etapa6.md).

## Arquitetura

```text
Navegador (React + TypeScript + Tailwind; Recharts só no painel)
   │  HTTP JSON (/api/*)
FastAPI ── app/main.py        rotas, CORS, cabeçalhos, limites, 503 e build estático
   ├── app/schemas.py         contratos Pydantic
   ├── app/security.py        limite de corpo e de requisições
   ├── app/public_data.py     agregados JSON pré-computados (web/backend/data)
   └── app/inference.py       carga única e lock
          └── final5.validation.SafeClassifier  (validação; fonte única das regras)
                 └── final5.pipeline.FinalPipeline → models/final (congelado)
```

O frontend não normaliza nem valida categorias: envia os valores devolvidos por `/api/options`. A busca sem acentos da lista de bairros só filtra opções; o valor enviado é sempre o selecionado. Requisições Pydantic usam campos `Any`, com `extra='forbid'`, para que nenhum valor seja convertido antes do `InputValidator`.

## API

| Rota | Função | Erros |
| --- | --- | --- |
| `GET /api/health` | Estado do serviço | 503 se modelo ou estatísticas faltarem |
| `GET /api/model` | Metadados públicos, sem hashes ou caminhos | 503 |
| `GET /api/options` | Vocabulário do contrato seguro | 503 |
| `POST /api/classify` | Classificação com o contrato 1.1.0 | 413, 422, 429, 503 |
| `GET /api/statistics` | Contagens agregadas | 503 |
| `GET /api/methodology` | Métricas publicadas das Etapas 4 e 5 e da auditoria | 503 |

Entrada de `POST /api/classify`, com exatamente quatro chaves:

```json
{"mes": 5, "dia_semana": 2, "tipo_local": "VIA PÚBLICA", "bairro": "BELA VISTA"}
```

Mês vai de 1 a 12 e dia de 0 (segunda) a 6 (domingo). `tipo_local` e `bairro` aceitam valores de `/api/options` ou `null` para ausência explícita. Sucesso e erro de validação seguem [o contrato seguro](../docs/contrato_inferencia_seguro.md). Falhas de serviço devolvem `{"status": "...", "mensagem": "..."}`.

## Agregados

`web/backend/data/*.json` são versionados, determinísticos e gerados por:

```powershell
.venv\Scripts\python web\backend\scripts\gerar_agregados.py
```

O script requer as bases locais em `data/processed`. Ele conta registros elegíveis e copia métricas já publicadas, sem carregar o modelo. A aplicação em execução não lê Parquet nem planilhas. Hashes das entradas ficam em `reports/etapa6/proveniencia_agregados.json`, que não é servido. Bairros não entram nos agregados.

## Dependências

- Python: `requirements-web.txt` (execução) e `requirements-web-dev.txt` (testes e agregados), sobre as versões fixadas em `requirements-final.txt`.
- JavaScript: `web/frontend/package.json`, com versões exatas em `package-lock.json`.
