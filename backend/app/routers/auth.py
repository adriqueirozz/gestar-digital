from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import auth, models
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["autenticacao"])


def _usuario_publico(u: models.Usuario) -> dict:
    return {"id": u.id, "nome": u.nome, "login": u.login, "perfil": u.perfil,
            "pode_editar": auth.pode_editar(u)}


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Recebe `username` e `password` (formulário) e devolve o token de acesso."""
    usuario = auth.autenticar(db, form.username, form.password)
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Login ou senha incorretos.",
                            headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": auth.criar_token(usuario), "token_type": "bearer",
            "usuario": _usuario_publico(usuario)}


@router.get("/me")
def quem_sou_eu(usuario: models.Usuario = Depends(auth.usuario_obrigatorio)):
    """Dados do usuário dono do token."""
    return _usuario_publico(usuario)
