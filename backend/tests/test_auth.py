"""Testes da autenticação e dos perfis (G-16)."""
from datetime import timedelta

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import auth, config, models
from app.database import Base, get_db
from app.main import app

SENHA = "segredo-123"


@pytest.fixture
def banco():
    # StaticPool: o TestClient roda em outra thread e precisa enxergar o mesmo banco em memória
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        yield sessao


@pytest.fixture
def client(banco):
    app.dependency_overrides[get_db] = lambda: banco
    yield TestClient(app)
    app.dependency_overrides.clear()


def criar_usuario(db, login="enf", perfil="enfermagem", ativo=True):
    u = models.Usuario(nome=f"Usuária {login}", login=login, perfil=perfil, ativo=ativo,
                       senha_hash=auth.gerar_hash_senha(SENHA))
    db.add(u)
    db.commit()
    return u


def entrar(client, login="enf", senha=SENHA):
    return client.post("/api/auth/login", data={"username": login, "password": senha})


def cabecalho(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------- senhas
def test_hash_de_senha():
    h = auth.gerar_hash_senha(SENHA)
    assert SENHA not in h
    assert auth.verificar_senha(SENHA, h)
    assert not auth.verificar_senha("errada", h)
    assert auth.gerar_hash_senha(SENHA) != h  # sal aleatório
    assert not auth.verificar_senha(SENHA, "lixo")


# ---------------------------------------------------------------- login
def test_login_devolve_token_e_perfil(client, banco):
    criar_usuario(banco, perfil="medico")
    r = entrar(client)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["token_type"] == "bearer"
    assert corpo["usuario"]["perfil"] == "medico"
    assert "senha_hash" not in corpo["usuario"]

    me = client.get("/api/auth/me", headers=cabecalho(corpo["access_token"]))
    assert me.status_code == 200
    assert me.json()["login"] == "enf"


def test_login_ignora_maiusculas_no_login(client, banco):
    criar_usuario(banco)
    assert entrar(client, login="  ENF ").status_code == 200


@pytest.mark.parametrize("login, senha", [("enf", "errada"), ("ninguem", SENHA)])
def test_login_invalido(client, banco, login, senha):
    criar_usuario(banco)
    r = entrar(client, login, senha)
    assert r.status_code == 401
    assert r.json()["detail"] == "Login ou senha incorretos."  # não revela se o login existe


def test_usuario_inativo_nao_entra(client, banco):
    criar_usuario(banco, ativo=False)
    assert entrar(client).status_code == 401


def test_usuario_desativado_perde_o_token(client, banco):
    u = criar_usuario(banco)
    token = entrar(client).json()["access_token"]
    u.ativo = False
    banco.commit()
    assert client.get("/api/auth/me", headers=cabecalho(token)).status_code == 401


# ---------------------------------------------------------------- tokens
def test_me_sem_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_token_invalido(client):
    assert client.get("/api/auth/me", headers=cabecalho("abc.def.ghi")).status_code == 401


def test_token_assinado_com_outra_chave(client, banco):
    u = criar_usuario(banco)
    falso = jwt.encode({"sub": str(u.id), "exp": models.agora() + timedelta(hours=1)}, "outra-chave-com-mais-de-32-caracteres!!", "HS256")
    assert client.get("/api/auth/me", headers=cabecalho(falso)).status_code == 401


def test_token_expirado(client, banco, monkeypatch):
    criar_usuario(banco)
    monkeypatch.setattr(config, "TOKEN_HORAS", -1)
    token = entrar(client).json()["access_token"]
    r = client.get("/api/auth/me", headers=cabecalho(token))
    assert r.status_code == 401
    assert "expirada" in r.json()["detail"]


# ---------------------------------------------------------------- rotas protegidas
def test_rotas_exigem_login_quando_ligado(client, banco, monkeypatch):
    monkeypatch.setattr(config, "EXIGIR_LOGIN", True)
    criar_usuario(banco)
    assert client.get("/api/painel").status_code == 401
    assert client.get("/api/pendencias/plantao").status_code == 401
    assert client.get("/health").status_code == 200  # saúde continua pública

    token = entrar(client).json()["access_token"]
    assert client.get("/api/painel", headers=cabecalho(token)).status_code == 200


def test_rotas_abertas_quando_login_desligado(client, monkeypatch):
    monkeypatch.setattr(config, "EXIGIR_LOGIN", False)
    assert client.get("/api/painel").status_code == 200


def test_token_invalido_e_recusado_mesmo_com_login_desligado(client, monkeypatch):
    monkeypatch.setattr(config, "EXIGIR_LOGIN", False)
    assert client.get("/api/painel", headers=cabecalho("abc")).status_code == 401


# ---------------------------------------------------------------- perfis
@pytest.fixture
def app_perfis(banco):
    """App mínima com uma rota restrita à enfermagem e ao médico."""
    mini = FastAPI()
    mini.dependency_overrides[get_db] = lambda: banco
    mini.include_router(__import__("app.routers.auth", fromlist=["router"]).router, prefix="/api")

    @mini.post("/acao", dependencies=[Depends(auth.exigir_perfil("enfermagem", "medico"))])
    def acao():
        return {"ok": True}

    return TestClient(mini)


@pytest.mark.parametrize("perfil, esperado", [("enfermagem", 200), ("medico", 200), ("gestao", 403)])
def test_exigir_perfil(app_perfis, banco, monkeypatch, perfil, esperado):
    monkeypatch.setattr(config, "EXIGIR_LOGIN", True)
    criar_usuario(banco, login=perfil, perfil=perfil)
    token = entrar(app_perfis, login=perfil).json()["access_token"]
    assert app_perfis.post("/acao", headers=cabecalho(token)).status_code == esperado


def test_exigir_perfil_sem_token(app_perfis, monkeypatch):
    monkeypatch.setattr(config, "EXIGIR_LOGIN", True)
    assert app_perfis.post("/acao").status_code == 401


def test_exigir_perfil_rejeita_perfil_desconhecido():
    with pytest.raises(ValueError):
        auth.exigir_perfil("enfermeira")


# ---------------------------------------------------------------- seed
def test_seed_cria_um_usuario_por_perfil_sem_duplicar(banco):
    from app.seed import USUARIOS, criar_usuarios

    assert criar_usuarios(banco) == 3
    banco.commit()
    assert criar_usuarios(banco) == 0  # rodar de novo não duplica
    perfis = {u.perfil for u in banco.query(models.Usuario)}
    assert perfis == set(auth.PERFIS)
    for u in USUARIOS:
        assert auth.autenticar(banco, u["login"], config.SENHA_DEMO) is not None


def test_seed_usa_a_senha_demo_configurada(banco, monkeypatch):
    from app.seed import criar_usuarios

    monkeypatch.setattr(config, "SENHA_DEMO", "outra-senha-do-prototipo")
    criar_usuarios(banco)
    banco.commit()
    assert auth.autenticar(banco, "gestao", "outra-senha-do-prototipo") is not None
    assert auth.autenticar(banco, "gestao", "gestar123") is None


# ---------------------------------------------------------------- tentativas de login (protótipo hospedado)
def test_muitas_senhas_erradas_bloqueiam_por_alguns_minutos(client, banco, monkeypatch):
    monkeypatch.setattr(config, "LOGIN_MAX_ERROS", 3)
    criar_usuario(banco)
    for _ in range(3):
        assert entrar(client, senha="errada").status_code == 401
    bloqueado = entrar(client)  # nem a senha certa entra durante o bloqueio
    assert bloqueado.status_code == 429
    assert "Tente de novo em" in bloqueado.json()["detail"]


def test_login_certo_zera_os_erros(client, banco, monkeypatch):
    monkeypatch.setattr(config, "LOGIN_MAX_ERROS", 3)
    criar_usuario(banco)
    for _ in range(2):
        entrar(client, senha="errada")
    assert entrar(client).status_code == 200
    for _ in range(2):
        entrar(client, senha="errada")
    assert entrar(client).status_code == 200  # não acumulou com os erros de antes


def test_bloqueio_passa_depois_do_tempo(client, banco, monkeypatch):
    monkeypatch.setattr(config, "LOGIN_MAX_ERROS", 2)
    criar_usuario(banco)
    agora = [1000.0]
    monkeypatch.setattr(auth.time, "monotonic", lambda: agora[0])
    entrar(client, senha="errada")
    entrar(client, senha="errada")
    assert entrar(client).status_code == 429
    agora[0] += config.LOGIN_BLOQUEIO_MIN * 60 + 1
    assert entrar(client).status_code == 200


# ---------------------------------------------------------------- produção
@pytest.mark.parametrize("chave, senha, exigir, ok", [
    ("x" * 40, "senha-do-prototipo", True, True),
    (config._CHAVE_PADRAO, "senha-do-prototipo", True, False),   # chave pública do repositório
    ("curta", "senha-do-prototipo", True, False),
    ("x" * 40, "gestar123", True, False),                         # senha do README
    ("x" * 40, "senha-do-prototipo", False, False),               # login desligado
])
def test_producao_recusa_configuracao_insegura(monkeypatch, chave, senha, exigir, ok):
    monkeypatch.setattr(config, "PRODUCAO", True)
    monkeypatch.setattr(config, "SECRET_KEY", chave)
    monkeypatch.setattr(config, "SENHA_DEMO", senha)
    monkeypatch.setattr(config, "EXIGIR_LOGIN", exigir)
    if ok:
        config.checar_producao()
    else:
        with pytest.raises(RuntimeError):
            config.checar_producao()


def test_desenvolvimento_aceita_os_padroes(monkeypatch):
    monkeypatch.setattr(config, "PRODUCAO", False)
    config.checar_producao()  # não levanta


def test_ip_inventado_a_esquerda_nao_escapa_do_bloqueio(client, banco, monkeypatch):
    monkeypatch.setattr(config, "LOGIN_MAX_ERROS", 2)
    criar_usuario(banco)
    for falso in ("1.1.1.1", "2.2.2.2"):
        client.post("/api/auth/login", data={"username": "enf", "password": "x"},
                    headers={"X-Forwarded-For": f"{falso}, 200.1.1.1"})
    r = client.post("/api/auth/login", data={"username": "enf", "password": SENHA},
                    headers={"X-Forwarded-For": "3.3.3.3, 200.1.1.1"})
    assert r.status_code == 429  # o IP acrescentado pelo proxy (200.1.1.1) é o mesmo
    outro = client.post("/api/auth/login", data={"username": "enf", "password": SENHA},
                        headers={"X-Forwarded-For": "200.9.9.9"})
    assert outro.status_code == 200  # outra pessoa não é afetada
