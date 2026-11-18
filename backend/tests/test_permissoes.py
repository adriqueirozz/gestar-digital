"""Gestão somente leitura (G-19) e registro de quem alterou cada informação (G-18)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import auth, config, models
from app.database import Base, get_db
from app.main import app
from app.seed import criar_catalogo


@pytest.fixture
def banco():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        criar_catalogo(sessao)
        sessao.commit()
        yield sessao


@pytest.fixture
def client(banco, monkeypatch):
    monkeypatch.setattr(config, "EXIGIR_LOGIN", True)
    app.dependency_overrides[get_db] = lambda: banco
    yield TestClient(app)
    app.dependency_overrides.clear()


def usuario(db, perfil, nome=None):
    u = models.Usuario(nome=nome or f"Usuária {perfil}", login=perfil, perfil=perfil, senha_hash="-")
    db.add(u)
    db.commit()
    return u


def como(u):
    return {"Authorization": f"Bearer {auth.criar_token(u)}"}


def paciente(db, n=1):
    p = models.Paciente(prontuario=str(900 + n), nome=f"Paciente {n}", chegada_em=models.agora())
    db.add(p)
    db.commit()
    return p


def pendencia(db, p):
    from app.services import pendencias
    return pendencias.criar(db, p, "Coletar exame", 12)


CSV = "leito;código do prontuário;data de entrada no COB;nome completo;GPA;IG;diagnóstico\n;123456;10/11/2026;Ana Teste;G1P0A0;39;TP\n"


def escritas(db):
    """Todas as rotas que alteram dados: (método, url, corpo json, arquivos)."""
    p = paciente(db)
    pend = pendencia(db, p)
    return [
        ("POST", f"/api/pacientes/{p.id}/alocar", {"destino": "E1A"}, None),
        ("POST", f"/api/pacientes/{p.id}/parto", {"tipo": "normal", "nascimento": "vivo"}, None),
        ("PATCH", f"/api/pacientes/{p.id}/sinalizacoes", {"atb": True}, None),
        ("POST", "/api/locais/E1B/situacao", {"situacao": "limpeza"}, None),
        ("PATCH", "/api/locais/M1", {"descricao": "Corredor"}, None),
        ("POST", "/api/pendencias", {"paciente_id": p.id, "descricao": "Nova", "prazo_horas": 12}, None),
        ("POST", f"/api/pendencias/{pend.id}/concluir", None, None),
        ("POST", "/api/importacoes", None, {"arquivo": ("teste.csv", CSV.encode(), "text/csv")}),
        # por último: depois da saída a paciente não aceita mais alterações
        ("POST", f"/api/pacientes/{p.id}/saida", {"desfecho": "casa"}, None),
    ]


def chamar(client, metodo, url, corpo, arquivos, headers):
    return client.request(metodo, url, json=corpo, files=arquivos, headers=headers)


# ---------------------------------------------------------------- G-19: Gestão somente leitura
def test_gestao_nao_altera_nada(client, banco):
    gestao = usuario(banco, "gestao")
    for metodo, url, corpo, arquivos in escritas(banco):
        r = chamar(client, metodo, url, corpo, arquivos, como(gestao))
        assert r.status_code == 403, (url, r.status_code, r.text)
        assert "permissão" in r.json()["detail"]
    # e nada mudou no banco
    assert banco.query(models.Movimentacao).count() == 0
    assert banco.query(models.Importacao).count() == 0


@pytest.mark.parametrize("perfil", ["enfermagem", "medico"])
def test_enfermagem_e_medico_alteram(client, banco, perfil):
    u = usuario(banco, perfil)
    for metodo, url, corpo, arquivos in escritas(banco):
        r = chamar(client, metodo, url, corpo, arquivos, como(u))
        assert r.status_code == 200, (url, r.status_code, r.text)


@pytest.mark.parametrize("perfil", ["enfermagem", "medico", "gestao"])
def test_todos_os_perfis_consultam(client, banco, perfil):
    u = usuario(banco, perfil)
    p = paciente(banco)
    for url in ("/api/painel", "/api/pendencias/plantao", "/api/locais/destinos",
                f"/api/pacientes/{p.id}", "/api/importacoes/ultima"):
        assert client.get(url, headers=como(u)).status_code == 200, url


def test_me_informa_se_pode_editar(client, banco):
    assert client.get("/api/auth/me", headers=como(usuario(banco, "gestao"))).json()["pode_editar"] is False
    assert client.get("/api/auth/me", headers=como(usuario(banco, "medico"))).json()["pode_editar"] is True


# ---------------------------------------------------------------- G-18: quem alterou
def test_movimentacao_parto_e_saida_registram_o_autor(client, banco):
    enf = usuario(banco, "enfermagem", "Ana Enfermeira")
    med = usuario(banco, "medico", "Bruno Médico")
    p = paciente(banco)

    client.post(f"/api/pacientes/{p.id}/alocar", json={"destino": "E1A"}, headers=como(enf))
    client.post(f"/api/pacientes/{p.id}/parto", json={"tipo": "normal", "nascimento": "vivo"}, headers=como(med))

    ficha = client.get(f"/api/pacientes/{p.id}", headers=como(enf)).json()
    assert ficha["historico"][0]["usuario"] == "Ana Enfermeira"
    assert ficha["parto"]["registrado_por"] == "Bruno Médico"

    client.post(f"/api/pacientes/{p.id}/saida", json={"desfecho": "casa"}, headers=como(med))
    saida = banco.query(models.Movimentacao).filter_by(paciente_id=p.id, motivo="saida").one()
    assert saida.usuario_id == med.id
    assert saida.data_hora is not None


def test_pendencia_registra_quem_criou_e_quem_concluiu(client, banco):
    enf = usuario(banco, "enfermagem", "Ana Enfermeira")
    med = usuario(banco, "medico", "Bruno Médico")
    p = paciente(banco)

    criada = client.post("/api/pendencias", json={"paciente_id": p.id, "descricao": "Coletar", "prazo_horas": 12},
                         headers=como(enf)).json()
    assert criada["criada_por"] == "Ana Enfermeira"
    assert criada["concluida_por"] is None

    concluida = client.post(f"/api/pendencias/{criada['id']}/concluir", headers=como(med)).json()
    assert concluida["concluida_por"] == "Bruno Médico"
    assert concluida["concluida_em"] is not None


def test_importacao_registra_quem_importou(client, banco):
    enf = usuario(banco, "enfermagem")
    client.post("/api/importacoes", files={"arquivo": ("t.csv", CSV.encode(), "text/csv")}, headers=como(enf))
    assert banco.query(models.Importacao).one().usuario_id == enf.id


def test_sem_login_obrigatorio_nao_quebra(banco, monkeypatch):
    """Com EXIGIR_LOGIN=false (só para depuração) as ações funcionam e ficam sem autor."""
    monkeypatch.setattr(config, "EXIGIR_LOGIN", False)
    app.dependency_overrides[get_db] = lambda: banco
    try:
        p = paciente(banco)
        r = TestClient(app).post(f"/api/pacientes/{p.id}/alocar", json={"destino": "E1A"})
        assert r.status_code == 200
        assert banco.query(models.Movimentacao).one().usuario_id is None
    finally:
        app.dependency_overrides.clear()
