from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.routers import health

from app.database import Base, engine
from app import models  # noqa: F401  (registra as tabelas)

from app.routers import health, painel, importacoes

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

Base.metadata.create_all(bind=engine)