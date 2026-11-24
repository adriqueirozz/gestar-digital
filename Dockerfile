# Protótipo hospedado do Gestar Digital: uma imagem só, com a API e as telas no mesmo endereço.
# Teste local:  docker build -t gestar . && docker run --rm -p 8000:8000 \
#   -e GESTAR_SECRET_KEY=<32+ caracteres aleatórios> -e GESTAR_SENHA_DEMO=<senha> gestar

# ---- Etapa 1: compila as telas (React + Vite) ----
FROM node:22-alpine AS telas
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Etapa 2: API em Python, que também entrega as telas compiladas ----
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    GESTAR_AMBIENTE=producao \
    GESTAR_SEED_AUTOMATICO=true \
    GESTAR_FRONTEND_DIST=/app/frontend/dist

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/app ./app
COPY --from=telas /frontend/dist /app/frontend/dist

# Não roda como administrador do sistema
RUN useradd --create-home --uid 10001 gestar && chown -R gestar /app/backend
USER gestar

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\",\"8000\")}/health')"
# O Render informa a porta em $PORT
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-server-header"]
