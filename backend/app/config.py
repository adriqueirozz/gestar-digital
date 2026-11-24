import os
from pathlib import Path

# ---- Ambiente ----
# "desenvolvimento" (padrão, máquina local) ou "producao" (protótipo hospedado).
# Em produção o sistema se recusa a subir com a chave e a senha de demonstração padrão.
AMBIENTE = os.getenv("GESTAR_AMBIENTE", "desenvolvimento").strip().lower()
PRODUCAO = AMBIENTE == "producao"

# Endereço do frontend em desenvolvimento (Vite). Em produção o próprio backend serve as telas (mesmo endereço).
CORS_ORIGINS = [o for o in os.getenv("CORS_ORIGINS", "" if PRODUCAO else "http://localhost:5173").split(",") if o]

# Banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gestar.db")

# Pasta com o build do frontend (npm run build). Se existir, o backend serve as telas.
FRONTEND_DIST = Path(os.getenv("GESTAR_FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))

# Cria o banco e os dados de demonstração ao subir, se estiver vazio (usado no protótipo hospedado).
SEED_AUTOMATICO = os.getenv("GESTAR_SEED_AUTOMATICO", "false").lower() in ("1", "true", "sim", "yes")

# ---- Autenticação (G-16) ----
# Chave usada para assinar os tokens. Em qualquer ambiente fora da máquina local,
# defina GESTAR_SECRET_KEY com um valor longo e aleatório.
_CHAVE_PADRAO = "dev-inseguro-troque-esta-chave-gestar-digital"
SECRET_KEY = os.getenv("GESTAR_SECRET_KEY", _CHAVE_PADRAO)
# Validade do token: um plantão.
TOKEN_HORAS = int(os.getenv("GESTAR_TOKEN_HORAS", "12"))
# Toda rota /api exige login (ligado no G-17, junto com a tela de login).
# EXIGIR_LOGIN=false libera as rotas sem token (útil só para depurar pela linha de comando).
EXIGIR_LOGIN = os.getenv("EXIGIR_LOGIN", "true").lower() in ("1", "true", "sim", "yes")

# Senha dos usuários de demonstração criados pelo seed. A padrão está no README (público): só serve na máquina local.
_SENHA_DEMO_PADRAO = "gestar123"
SENHA_DEMO = os.getenv("GESTAR_SENHA_DEMO", _SENHA_DEMO_PADRAO)

# Proteção contra tentativa de adivinhar senha: bloqueia o IP depois de N erros seguidos, por alguns minutos.
LOGIN_MAX_ERROS = int(os.getenv("GESTAR_LOGIN_MAX_ERROS", "8"))
LOGIN_BLOQUEIO_MIN = int(os.getenv("GESTAR_LOGIN_BLOQUEIO_MIN", "15"))

# Tamanho máximo da planilha enviada na importação.
IMPORTACAO_MAX_MB = int(os.getenv("GESTAR_IMPORTACAO_MAX_MB", "5"))


def checar_producao() -> None:
    """Impede o protótipo hospedado de subir com segredos que estão públicos no repositório."""
    if not PRODUCAO:
        return
    problemas = []
    if SECRET_KEY == _CHAVE_PADRAO or len(SECRET_KEY) < 32:
        problemas.append("defina GESTAR_SECRET_KEY com um valor aleatório de pelo menos 32 caracteres")
    if SENHA_DEMO == _SENHA_DEMO_PADRAO or len(SENHA_DEMO) < 8:
        problemas.append("defina GESTAR_SENHA_DEMO com uma senha de pelo menos 8 caracteres, diferente da do README")
    if not EXIGIR_LOGIN:
        problemas.append("EXIGIR_LOGIN não pode ser desligado em produção")
    if problemas:
        raise RuntimeError("Configuração insegura para produção: " + "; ".join(problemas) + ".")
