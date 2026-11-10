# Implantação da plataforma web — Etapa 6

**Estado: preparada, não publicada.** Nenhuma conta de hospedagem foi usada e não existe URL pública. A publicação depende de autorização e de uma hospedagem escolhida pelo responsável.

## Abordagem recomendada

Um único contêiner serve a API, a Dense64 e o build do frontend na mesma origem, o que dispensa CORS. O [`Dockerfile`](../Dockerfile) copia somente `src/`, `models/final/`, a API e os agregados; o `.dockerignore` funciona como lista de permissão e deixa de fora datasets, relatórios e segredos.

**Os artefatos não estão no Git.** `modelo.keras` e `preprocessador.joblib` são ignorados, então a imagem precisa ser construída em uma cópia local que os contenha. Uma hospedagem que construa a partir de um clone não os encontrará, e a API responderá 503 em vez de classificar. Prefira construir localmente e enviar a imagem pronta a um registro.

## Procedimento

Com o Docker em execução, na raiz do projeto:

```powershell
docker build -t gs-celulares-web:1.0.0 .
docker run --rm -p 8000:8000 -e APP_ENV=production gs-celulares-web:1.0.0
```

Abra `http://127.0.0.1:8000`, confirme que `/api/health` responde `status: ok` e execute uma classificação. Depois, envie a imagem ao registro da hospedagem seguindo a documentação dela.

**Evidência atual:** o Docker Desktop estava instalado, porém desligado, e a imagem **não foi construída** nesta etapa. Verificou-se o mesmo layout de arquivos em uma pasta limpa, sem `.runtime*`, datasets ou relatórios: `/api/health` e uma classificação real funcionaram, com o build servido em modo de produção. Execute o procedimento acima antes de publicar.

## Variáveis de ambiente

| Variável | Padrão | Uso |
| --- | --- | --- |
| `PORT` | `8000` (imagem) | Porta do Uvicorn; muitas hospedagens a definem |
| `APP_ENV` | `development` local, `production` na imagem | `production` desativa `/api/docs` |
| `CORS_ORIGINS` | origens locais do Vite | Lista exata separada por vírgulas; curinga é recusado |
| `RATE_LIMIT_PER_MINUTE` | `60` | Classificações por IP e por processo |
| `MAX_BODY_BYTES` | `2048` | Tamanho máximo do corpo |
| `MODEL_DIR`, `DATA_DIR`, `FRONTEND_DIST` | caminhos do projeto | Substituições opcionais |
| `FORWARDED_ALLOW_IPS` | somente local | Lida pelo Uvicorn. Defina com os IPs do proxy para o limite usar o IP real do visitante. Use `*` apenas se o contêiner só for alcançável pelo proxy |
| `VITE_API_BASE_URL` | vazia | No build do frontend, somente se a API estiver em outra origem |

## Frontend e API separados

Só use esta alternativa se a hospedagem exigir. Gere o frontend com `VITE_API_BASE_URL=<origem da API>` e `npm run build`, publique `web/frontend/dist` com redirecionamento das rotas `/painel` e `/sobre` para `index.html` e defina `CORS_ORIGINS` na API com a origem exata do frontend.

## Requisitos de hospedagem

- Suporte a contêiner Linux ou Python 3.12, com TensorFlow CPU 2.20.
- Memória: o processo usou cerca de 343 MB após carregar o modelo e atender 300 classificações (medição local, em Windows). Reserve ao menos 1 GB para acomodar variações e picos.
- Processador: 1 vCPU basta para a demonstração; a mediana foi de cerca de 4 ms por classificação, sem contar a rede.
- Armazenamento suficiente para a imagem com TensorFlow, cujo tamanho não foi medido.
- Inicialização: cerca de 5 segundos localmente, antes de `/api/health` responder. Configure um período de início tolerante.
- Use um único worker por instância: cada worker carrega o modelo e mantém seu próprio limite de requisições. Com várias instâncias, o limite não é compartilhado.

## Segurança antes de publicar

- Sirva somente por HTTPS, na borda da hospedagem.
- Mantenha `APP_ENV=production` e confirme que `/api/docs` responde 404.
- Não envie `data/`, `reports/private/` ou arquivos `.env` à hospedagem.
- A aplicação não tem autenticação nem controles antiabuso além do limite por IP, adequados apenas a uma demonstração.
- Não registre entradas de visitantes nem as use para retreinar o modelo.
