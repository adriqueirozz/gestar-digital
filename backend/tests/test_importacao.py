"""Teste de integração: planilha de exemplo -> banco. Usa o fixture `db` do conftest.py."""
from pathlib import Path

from app import models
from app.services import importacao

CSV = Path(__file__).resolve().parents[2] / "data" / "sample" / "pacientes_teste.csv"


def criar_catalogo(db):
    for n in range(1, 10):
        for letra in "ABC":
            db.add(models.Localizacao(codigo=f"E{n}{letra}", tipo="leito",
                                      nome=f"Enf. {n} · Leito {letra}", enfermaria=n))
    db.commit()


def test_importacao_completa(db):
    criar_catalogo(db)
    r = importacao.importar(db, CSV.read_bytes(), CSV.name)

    assert r["linhas_lidas"] == 13
    assert r["novas"] == 12 and r["ignoradas"] == 1
    assert r["alocadas"] == 8 and r["na_fila"] == 4
    assert r["linhas_com_problema"] == 5

    tipos = {p["tipo"] for p in r["problemas"]}
    assert {"prontuario_invalido", "campo_vazio", "formato_invalido",
            "leito_inexistente", "leito_ocupado"} <= tipos

    joana = db.query(models.Paciente).filter_by(prontuario="104521").one()
    assert joana.localizacao.codigo == "E1A"
    assert joana.perfil == "gestante" and joana.chegada_tem_hora is False
    assert joana.dados_origem["nome completo"] == "Joana Maria Lima"
    assert len(joana.movimentacoes) == 1

    bruna = db.query(models.Paciente).filter_by(prontuario="105001").one()  # leito E1A já ocupado
    assert bruna.localizacao_id is None

    renata = db.query(models.Paciente).filter_by(prontuario="104700").one()  # "E3A" normalizado
    assert renata.localizacao.codigo == "E3A"


def test_reimportacao_nao_mexe_na_localizacao(db):
    criar_catalogo(db)
    importacao.importar(db, CSV.read_bytes(), CSV.name)

    # a enfermagem muda a Joana de leito no Gestar
    joana = db.query(models.Paciente).filter_by(prontuario="104521").one()
    novo = db.query(models.Localizacao).filter_by(codigo="E7A").one()
    joana.localizacao_id = novo.id
    db.commit()

    r = importacao.importar(db, CSV.read_bytes(), CSV.name)
    assert r["novas"] == 0 and r["atualizadas"] == 12

    db.refresh(joana)
    assert joana.localizacao.codigo == "E7A"                      # continua onde o Gestar colocou
    assert any(p["tipo"] == "divergencia" for p in r["problemas"])  # e a divergência é sinalizada