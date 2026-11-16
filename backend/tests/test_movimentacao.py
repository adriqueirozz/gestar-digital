import pytest
from fastapi import HTTPException

from app import models
from app.services import movimentacao


def catalogo(db):
    for codigo, tipo in (("E1A", "leito"), ("E1B", "leito"), ("PN1", "sala_parto")):
        db.add(models.Localizacao(codigo=codigo, tipo=tipo, nome=codigo, enfermaria=1 if tipo == "leito" else None))
    db.commit()


def paciente(db, n=1):
    p = models.Paciente(prontuario=str(900 + n), nome=f"Paciente {n}", chegada_em=models.agora())
    db.add(p)
    db.commit()
    return p


def local(db, codigo):
    return db.query(models.Localizacao).filter_by(codigo=codigo).one()


def test_alocar_e_mover_deixa_leito_em_limpeza(db):
    catalogo(db)
    p = paciente(db)
    movimentacao.alocar(db, p, "E1A")
    movimentacao.alocar(db, p, "E1B")
    assert local(db, "E1A").situacao == "limpeza"
    assert p.localizacao.codigo == "E1B"
    assert sorted(m.motivo for m in p.movimentacoes) == ["alocacao", "movimentacao"]


def test_recusa_leito_ocupado_e_em_limpeza(db):
    catalogo(db)
    a, b = paciente(db, 1), paciente(db, 2)
    movimentacao.alocar(db, a, "E1A")
    with pytest.raises(HTTPException) as erro:
        movimentacao.alocar(db, b, "E1A")
    assert erro.value.status_code == 409
    movimentacao.alocar(db, a, "E1B")          # E1A vira limpeza
    with pytest.raises(HTTPException):
        movimentacao.alocar(db, b, "E1A")


def test_parto_vira_puerpera_e_nao_duplica(db):
    catalogo(db)
    p = paciente(db)
    p.parindo = True
    db.commit()
    movimentacao.registrar_parto(db, p, "normal", "vivo")
    assert p.perfil == "puerpera" and p.parindo is False
    with pytest.raises(HTTPException):
        movimentacao.registrar_parto(db, p, "normal", "vivo")


def test_saida_libera_leito_e_bloqueia_novas_acoes(db):
    catalogo(db)
    p = paciente(db)
    movimentacao.alocar(db, p, "E1A")
    movimentacao.registrar_saida(db, p, "casa")
    assert p.status == "saiu" and p.localizacao_id is None and p.desfecho == "casa"
    assert local(db, "E1A").situacao == "limpeza"
    with pytest.raises(HTTPException):
        movimentacao.alocar(db, p, "E1B")


def test_nova_maca_some_ao_mover(db):
    catalogo(db)
    p = paciente(db)
    movimentacao.alocar(db, p, "NOVA_MACA", local_maca="Corredor")
    maca = local(db, "M1")
    assert maca.descricao == "Corredor" and maca.ativa
    movimentacao.alocar(db, p, "E1A")
    assert local(db, "M1").ativa is False


def test_data_no_futuro_e_recusada(db):
    with pytest.raises(HTTPException):
        movimentacao.data_ou_agora("2999-01-01T10:00")