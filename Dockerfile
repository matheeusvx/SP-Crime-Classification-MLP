# Etapa 6: imagem única com API, Dense64 congelada e build do frontend.
# Construir localmente, pois models/final não é versionado no Git.
FROM node:22-alpine AS frontend
WORKDIR /build
COPY web/frontend/package.json web/frontend/package-lock.json ./
RUN npm ci
COPY web/frontend/ ./
RUN npx vite build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production PORT=8000 \
    TF_CPP_MIN_LOG_LEVEL=2 FRONTEND_DIST=/app/web/frontend/dist
WORKDIR /app
COPY requirements-final.txt requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt
COPY src/ ./src/
COPY models/final/ ./models/final/
COPY web/backend/app/ ./web/backend/app/
COPY web/backend/data/ ./web/backend/data/
COPY --from=frontend /build/dist/ ./web/frontend/dist/
RUN useradd --no-create-home --uid 10001 app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import os,urllib.request as u; u.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/health', timeout=4)"
CMD ["sh", "-c", "exec uvicorn app.main:app --app-dir web/backend --host 0.0.0.0 --port ${PORT} --proxy-headers"]
