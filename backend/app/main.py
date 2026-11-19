from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS

from app.database import Base, engine
from app import models  # noqa: F401  (registra as tabelas)
from app.auth import usuario_atual

from app.routers import auth, health, painel, importacoes, pacientes, locais, pendencias

app = FastAPI(title="Gestar Digital API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api")           # /api/auth/login, /api/auth/me (públicas)

# Todas as rotas abaixo passam pela checagem de login (G-16).
# Restrições por perfil ficam em cada rota, com Depends(exigir_perfil(...)).
protegida = [Depends(usuario_atual)]
app.include_router(painel.router, prefix="/api", dependencies=protegida)
app.include_router(importacoes.router, prefix="/api", dependencies=protegida)
app.include_router(pacientes.router, prefix="/api", dependencies=protegida)   # /api/pacientes/{id}...
app.include_router(locais.router, prefix="/api", dependencies=protegida)      # /api/locais/...
app.include_router(pendencias.router, prefix="/api", dependencies=protegida)  # /api/pendencias

Base.metadata.create_all(bind=engine)
