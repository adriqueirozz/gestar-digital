"""Autenticação e perfis (G-16).

- Senhas guardadas com PBKDF2-SHA256 (biblioteca padrão do Python), nunca em texto puro.
- Login devolve um token JWT assinado com SECRET_KEY, válido por TOKEN_HORAS.
- `usuario_atual` identifica quem está chamando a API; `exigir_perfil` restringe uma rota a perfis.
"""
import base64
import hashlib
import hmac
import os
from datetime import timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app import config, models
from app.database import get_db

PERFIS = ("enfermagem", "medico", "gestao")

_ALGORITMO_HASH = "pbkdf2_sha256"
_ITERACOES = 260_000
_ALGORITMO_TOKEN = "HS256"

# tokenUrl faz o botão "Authorize" do /docs funcionar com login e senha
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ---------------------------------------------------------------- senhas
def gerar_hash_senha(senha: str) -> str:
    sal = os.urandom(16)
    chave = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal, _ITERACOES)
    return "$".join((_ALGORITMO_HASH, str(_ITERACOES),
                     base64.b64encode(sal).decode(), base64.b64encode(chave).decode()))


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        algoritmo, iteracoes, sal, chave = senha_hash.split("$")
        if algoritmo != _ALGORITMO_HASH:
            return False
        calculada = hashlib.pbkdf2_hmac("sha256", senha.encode(), base64.b64decode(sal), int(iteracoes))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calculada, base64.b64decode(chave))


# ---------------------------------------------------------------- tokens
def criar_token(usuario: models.Usuario) -> str:
    agora = models.agora()
    dados = {"sub": str(usuario.id), "perfil": usuario.perfil,
             "iat": agora, "exp": agora + timedelta(hours=config.TOKEN_HORAS)}
    return jwt.encode(dados, config.SECRET_KEY, algorithm=_ALGORITMO_TOKEN)


def _nao_autenticado(detalhe: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail=detalhe, headers={"WWW-Authenticate": "Bearer"})


def autenticar(db: Session, login: str, senha: str) -> models.Usuario | None:
    usuario = db.query(models.Usuario).filter(models.Usuario.login == login.strip().lower()).first()
    if usuario is None or not usuario.ativo or not verificar_senha(senha, usuario.senha_hash):
        return None
    return usuario


def usuario_do_token(db: Session, token: str) -> models.Usuario:
    try:
        dados = jwt.decode(token, config.SECRET_KEY, algorithms=[_ALGORITMO_TOKEN])
        usuario_id = int(dados["sub"])
    except jwt.ExpiredSignatureError:
        raise _nao_autenticado("Sessão expirada. Entre novamente.")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise _nao_autenticado("Token inválido.")
    usuario = db.get(models.Usuario, usuario_id)
    if usuario is None or not usuario.ativo:
        raise _nao_autenticado("Usuário inativo ou inexistente.")
    return usuario


# ---------------------------------------------------------------- dependências das rotas
def usuario_atual(token: str | None = Depends(oauth2), db: Session = Depends(get_db)) -> models.Usuario | None:
    """Usuário logado. Sem token: erro 401 se EXIGIR_LOGIN, senão None (modo sem login, até o G-17)."""
    if token:
        return usuario_do_token(db, token)
    if config.EXIGIR_LOGIN:
        raise _nao_autenticado("É preciso entrar no sistema.")
    return None


def usuario_obrigatorio(usuario: models.Usuario | None = Depends(usuario_atual)) -> models.Usuario:
    """Para rotas que precisam saber quem é o usuário mesmo com EXIGIR_LOGIN desligado (ex.: /auth/me)."""
    if usuario is None:
        raise _nao_autenticado("É preciso entrar no sistema.")
    return usuario


def exigir_perfil(*perfis: str):
    """Dependência que libera a rota só para os perfis informados. Uso:
        @router.post("", dependencies=[Depends(exigir_perfil("enfermagem", "medico"))])
    """
    desconhecidos = set(perfis) - set(PERFIS)
    if desconhecidos:
        raise ValueError(f"Perfis desconhecidos: {sorted(desconhecidos)}")

    def checar(usuario: models.Usuario | None = Depends(usuario_atual)) -> models.Usuario | None:
        if usuario is None:  # modo sem login: não há perfil para checar
            return None
        if usuario.perfil not in perfis:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Seu perfil não tem permissão para esta ação.")
        return usuario

    return checar
