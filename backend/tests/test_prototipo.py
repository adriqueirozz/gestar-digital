"""Protótipo hospedado: telas servidas pela API, cabeçalhos de segurança, /docs desligado e limite do upload."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import auth, config, models
from app.database import Base, get_db
from app.main import criar_app


@pytest.fixture
def dist(tmp_path):
    """Um build falso do frontend."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>tela do gestar</html>", encoding="utf-8")
    (tmp_path / "assets" / "app-123.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path.parent / "segredo.txt").write_text("não pode sair", encoding="utf-8")
    return tmp_path


@pytest.fixture
def producao(monkeypatch, dist):
    monkeypatch.setattr(config, "PRODUCAO", True)
    monkeypatch.setattr(config, "SECRET_KEY", "x" * 40)
    monkeypatch.setattr(config, "SENHA_DEMO", "senha-do-prototipo")
    monkeypatch.setattr(config, "CORS_ORIGINS", [])
    monkeypatch.setattr(config, "FRONTEND_DIST", dist)
    return TestClient(criar_app())


def test_telas_do_react_saem_no_mesmo_endereco(producao):
    for rota in ("/", "/pendencias", "/relatorio", "/login"):
        r = producao.get(rota)
        assert r.status_code == 200 and "tela do gestar" in r.text, rota
    assert producao.get("/assets/app-123.js").text == "console.log(1)"
    assert producao.get("/favicon.svg").text == "<svg/>"


def test_api_continua_respondendo_e_rota_inexistente_da_404(producao):
    assert producao.get("/health").json() == {"status": "ok"}
    assert producao.get("/api/painel").status_code == 401      # exige login, não devolve a tela
    assert producao.get("/api/nao-existe").status_code == 404


def test_nao_vaza_arquivo_fora_da_pasta_do_build(producao):
    for rota in ("/../segredo.txt", "/%2e%2e/segredo.txt", "/assets/../../segredo.txt"):
        assert "não pode sair" not in producao.get(rota).text


def test_docs_desligado_em_producao(producao):
    assert "swagger" not in producao.get("/docs").text.lower()
    assert producao.get("/openapi.json").headers["content-type"].startswith("text/html")  # cai na tela, sem o esquema


def test_cabecalhos_de_seguranca_em_producao(producao):
    h = producao.get("/").headers
    assert h["X-Frame-Options"] == "DENY"
    assert h["X-Content-Type-Options"] == "nosniff"
    assert "noindex" in h["X-Robots-Tag"]
    assert "frame-ancestors 'none'" in h["Content-Security-Policy"]
    assert "max-age" in h["Strict-Transport-Security"]


def test_producao_nao_sobe_com_os_segredos_do_repositorio(monkeypatch):
    monkeypatch.setattr(config, "PRODUCAO", True)
    monkeypatch.setattr(config, "SECRET_KEY", config._CHAVE_PADRAO)
    with pytest.raises(RuntimeError):
        criar_app()


def test_desenvolvimento_continua_com_docs_e_sem_build(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "PRODUCAO", False)
    monkeypatch.setattr(config, "FRONTEND_DIST", tmp_path / "nao-existe")
    c = TestClient(criar_app())
    assert c.get("/docs").status_code == 200
    assert c.get("/pendencias").status_code == 404   # sem build, a API não serve telas
    assert "Content-Security-Policy" not in c.get("/health").headers


def test_planilha_grande_demais_e_recusada(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    banco = Session(engine)
    u = models.Usuario(nome="Enf", login="enf", perfil="enfermagem", senha_hash=auth.gerar_hash_senha("s"))
    banco.add(u)
    banco.commit()
    monkeypatch.setattr(config, "IMPORTACAO_MAX_MB", 1)
    app = criar_app()
    app.dependency_overrides[get_db] = lambda: banco
    c = TestClient(app)
    token = auth.criar_token(u)
    grande = b"x" * (1024 * 1024 + 10)
    r = c.post("/api/importacoes", files={"arquivo": ("p.csv", grande, "text/csv")},
               headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 413
    assert "máximo 1 MB" in r.json()["detail"]
