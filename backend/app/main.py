from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS

from app.database import Base, engine
from app import models  # noqa: F401  (registra as tabelas)

from app.routers import health, painel, importacoes, pacientes, locais, pendencias

app = FastAPI(title="Gestar Digital API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)

app.include_router(painel.router, prefix="/api") 
app.include_router(importacoes.router, prefix="/api")   
app.include_router(pacientes.router, prefix="/api")   # /api/pacientes/{id}...
app.include_router(locais.router, prefix="/api")      # /api/locais/...
app.include_router(pendencias.router, prefix="/api")   # /api/pendencias

Base.metadata.create_all(bind=engine)