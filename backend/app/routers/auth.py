from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import auth, models
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["autenticacao"])


def _usuario_publico(u: models.Usuario) -> dict:
    return {"id": u.id, "nome": u.nome, "login": u.login, "perfil": u.perfil,
            "pode_editar": auth.pode_editar(u)}


def _origem(request: Request) -> str:
    """IP de quem tenta entrar, para o bloqueio por senha errada.
    No protótipo hospedado há proxies na frente (Cloudflare/Render). O valor mais à DIREITA do X-Forwarded-For
    é o que o último proxy acrescentou; os da esquerda podem ter sido inventados por quem fez a requisição."""
    cloudflare = request.headers.get("cf-connecting-ip")
    if cloudflare:
        return cloudflare.strip()
    encaminhado = [ip.strip() for ip in request.headers.get("x-forwarded-for", "").split(",") if ip.strip()]
    if encaminhado:
        return encaminhado[-1]
    return request.client.host if request.client else "desconhecida"


@router.post("/login")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Recebe `username` e `password` (formulário) e devolve o token de acesso.
    Depois de muitas senhas erradas seguidas, a mesma origem (IP) fica bloqueada por alguns minutos."""
    origem = _origem(request)
    minutos = auth.minutos_de_bloqueio(origem)
    if minutos:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Muitas tentativas de login. Tente de novo em {minutos} min.")
    usuario = auth.autenticar(db, form.username, form.password)
    if usuario is None:
        auth.registrar_erro_login(origem)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Login ou senha incorretos.",
                            headers={"WWW-Authenticate": "Bearer"})
    auth.limpar_erros_login(origem)
    return {"access_token": auth.criar_token(usuario), "token_type": "bearer",
            "usuario": _usuario_publico(usuario)}


@router.get("/me")
def quem_sou_eu(usuario: models.Usuario = Depends(auth.usuario_obrigatorio)):
    """Dados do usuário dono do token."""
    return _usuario_publico(usuario)
