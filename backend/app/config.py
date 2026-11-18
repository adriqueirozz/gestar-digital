import os

# Endereço do frontend em desenvolvimento (Vite)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# Banco de dados (será usado no G-06)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gestar.db")

# ---- Autenticação (G-16) ----
# Chave usada para assinar os tokens. Em qualquer ambiente fora da máquina local,
# defina GESTAR_SECRET_KEY com um valor longo e aleatório.
SECRET_KEY = os.getenv("GESTAR_SECRET_KEY", "dev-inseguro-troque-esta-chave-gestar-digital")
# Validade do token: um plantão.
TOKEN_HORAS = int(os.getenv("GESTAR_TOKEN_HORAS", "12"))
# Toda rota /api exige login (ligado no G-17, junto com a tela de login).
# EXIGIR_LOGIN=false libera as rotas sem token (útil só para depurar pela linha de comando).
EXIGIR_LOGIN = os.getenv("EXIGIR_LOGIN", "true").lower() in ("1", "true", "sim", "yes")
