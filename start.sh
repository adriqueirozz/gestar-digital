#!/usr/bin/env bash
# Sobe o Gestar Digital inteiro (backend + frontend) com um comando só.
# Uso (Git Bash no Windows, Linux ou macOS), na raiz do projeto:
#   ./start.sh            -> sobe tudo (na 1a vez instala dependências e cria o banco)
#   ./start.sh --recriar  -> apaga o banco e popula de novo com dados simulados
# Para parar: Ctrl+C (derruba backend e frontend juntos).

set -e

RAIZ="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$RAIZ/backend"
FRONTEND="$RAIZ/frontend"

info() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }
erro() { printf '\n\033[1;31mERRO: %s\033[0m\n' "$1" >&2; exit 1; }

# ---------- Pré-requisitos ----------
if command -v python >/dev/null 2>&1 && python --version >/dev/null 2>&1; then
  PY=python
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v py >/dev/null 2>&1; then
  PY=py
else
  erro "Python não encontrado. Instale o Python 3.11+ (marque 'Add Python to PATH')."
fi
command -v npm >/dev/null 2>&1 || erro "Node.js/npm não encontrado. Instale o Node.js 20+."

# ---------- Backend ----------
cd "$BACKEND"

if [ ! -d .venv ]; then
  info "Criando ambiente virtual (.venv)"
  "$PY" -m venv .venv
fi

if [ -f .venv/Scripts/python.exe ]; then
  VPY="$BACKEND/.venv/Scripts/python.exe"   # Windows
else
  VPY="$BACKEND/.venv/bin/python"           # Linux/macOS
fi

REQ=requirements.txt
[ -f requirements-dev.txt ] && REQ=requirements-dev.txt
# Só reinstala quando o arquivo de dependências mudar
if [ ! -f .venv/.instalado ] || [ "$REQ" -nt .venv/.instalado ]; then
  info "Instalando dependências do backend ($REQ)"
  "$VPY" -m pip install --upgrade pip -q
  "$VPY" -m pip install -r "$REQ" -q
  touch .venv/.instalado
fi

if [ "$1" = "--recriar" ]; then
  info "Recriando o banco com dados simulados"
  "$VPY" -m app.seed --recriar
elif [ ! -f gestar.db ]; then
  info "Criando o banco com dados simulados"
  "$VPY" -m app.seed
fi

# ---------- Frontend ----------
cd "$FRONTEND"

if [ ! -d node_modules ] || [ package.json -nt node_modules ] || [ package-lock.json -nt node_modules ]; then
  info "Instalando dependências do frontend (npm install)"
  npm install
  touch node_modules
fi

[ -f .env ] || { [ -f env.example ] && cp env.example .env; }

# ---------- Subir os serviços ----------
PIDS=()
parar() {
  info "Parando os serviços..."
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  # No Windows os filhos (uvicorn/vite) podem sobrar; garante que morram
  if command -v taskkill >/dev/null 2>&1; then
    for pid in "${PIDS[@]}"; do
      wpid=$(cat /proc/"$pid"/winpid 2>/dev/null || true)
      [ -n "$wpid" ] && taskkill //F //T //PID "$wpid" >/dev/null 2>&1 || true
    done
  fi
  exit 0
}
trap parar INT TERM EXIT

info "Subindo a API em http://localhost:8000"
cd "$BACKEND"
"$VPY" -m uvicorn app.main:app --reload --port 8000 &
PIDS+=($!)

info "Subindo o frontend em http://localhost:5173"
cd "$FRONTEND"
npm run dev -- --port 5173 &
PIDS+=($!)

# Espera a API responder e abre o navegador
for _ in $(seq 1 30); do
  if curl -fs http://localhost:8000/health >/dev/null 2>&1; then break; fi
  sleep 1
done
sleep 2
URL=http://localhost:5173
if [ -n "$NO_BROWSER" ]; then :
elif command -v cmd.exe >/dev/null 2>&1; then cmd.exe //c start "" "$URL" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then open "$URL" >/dev/null 2>&1 || true
fi

printf '\n\033[1;32mGestar Digital rodando!\033[0m\n'
printf '  Frontend: http://localhost:5173\n'
printf '  API:      http://localhost:8000  (docs: http://localhost:8000/docs)\n'
printf '  Ctrl+C para parar tudo.\n\n'

wait
