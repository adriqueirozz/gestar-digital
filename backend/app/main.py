from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.database import Base, engine
from app import models  # noqa: F401  (registra as tabelas)
from app.auth import usuario_atual

from app.routers import auth, health, painel, importacoes, pacientes, locais, pendencias, relatorios

# Cabeçalhos de segurança enviados em toda resposta.
CABECALHOS_SEGURANCA = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",                      # ninguém embute o sistema dentro de outro site
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "X-Robots-Tag": "noindex, nofollow",            # protótipo não aparece no Google
}
# Só no protótipo hospedado (sempre em HTTPS): força HTTPS e limita de onde vêm scripts, estilos e fontes.
CABECALHOS_PRODUCAO = {
    "Strict-Transport-Security": "max-age=31536000",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
}


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    if config.SEED_AUTOMATICO:
        # Protótipo hospedado: o disco é apagado a cada reinício, então o banco nasce de novo com os dados de demonstração.
        from app.seed import seed
        seed()
    yield


def _servir_frontend(app: FastAPI, pasta: Path) -> None:
    """Serve o build do React (frontend/dist) no mesmo endereço da API. Sem build, não faz nada (desenvolvimento)."""
    index = pasta / "index.html"
    if not index.is_file():
        return
    raiz = pasta.resolve()
    if (raiz / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=raiz / "assets"), name="assets")

    @app.get("/{caminho:path}", include_in_schema=False)
    def frontend(caminho: str):
        if caminho == "api" or caminho.startswith("api/"):
            raise HTTPException(status_code=404, detail="Rota não encontrada.")
        arquivo = (raiz / caminho).resolve()
        if caminho and arquivo.is_file() and arquivo.is_relative_to(raiz):
            return FileResponse(arquivo)
        # Qualquer outra rota (/pendencias, /relatorio...) é uma tela do React: devolve o index.html.
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


def criar_app() -> FastAPI:
    config.checar_producao()

    # Em produção a documentação interativa da API (/docs) fica desligada.
    docs = {} if not config.PRODUCAO else {"docs_url": None, "redoc_url": None, "openapi_url": None}
    app = FastAPI(title="Gestar Digital API", lifespan=ciclo_de_vida, **docs)

    if config.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.CORS_ORIGINS,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    cabecalhos = {**CABECALHOS_SEGURANCA, **(CABECALHOS_PRODUCAO if config.PRODUCAO else {})}

    @app.middleware("http")
    async def cabecalhos_de_seguranca(request, call_next):
        resposta = await call_next(request)
        for nome, valor in cabecalhos.items():
            resposta.headers.setdefault(nome, valor)
        return resposta

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
    app.include_router(relatorios.router, prefix="/api", dependencies=protegida)

    _servir_frontend(app, config.FRONTEND_DIST)  # por último: não pode esconder as rotas da API
    return app


Base.metadata.create_all(bind=engine)
app = criar_app()
