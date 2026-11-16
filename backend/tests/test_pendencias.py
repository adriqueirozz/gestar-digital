from datetime import timedelta

import pytest
from fastapi import HTTPException

from app import models
from app.services import pendencias as srv


def paciente(db, n=1, status="ativa"):
    p = models.Paciente(prontuario=str(800 + n), nome=f"Paciente {n}", chegada_em=models.agora(), status=status)
    db.add(p)
    db.commit()
    return p


def test_prazo_e_situacoes(db):
    pend = srv.criar(db, paciente(db), "Coletar exame", 12)
    assert pend.vence_em - pend.criada_em == timedelta(hours=12)
    assert srv.situacao(pend, models.agora()) == "em_dia"
    assert srv.situacao(pend, pend.vence_em - timedelta(hours=2)) == "proxima"
    assert srv.situacao(pend, pend.vence_em + timedelta(minutes=5)) == "vencida"


def test_concluir_uma_vez(db):
    pend = srv.criar(db, paciente(db), "Coletar exame", 24)
    srv.concluir(db, pend)
    assert srv.situacao(pend, models.agora()) == "concluida"
    with pytest.raises(HTTPException):
        srv.concluir(db, pend)


def test_validacoes(db):
    p = paciente(db)
    with pytest.raises(HTTPException) as erro:
        srv.criar(db, p, "Algo", 6)
    assert erro.value.status_code == 422
    with pytest.raises(HTTPException):
        srv.criar(db, p, "   ", 12)
    saiu = paciente(db, 2, status="saiu")
    with pytest.raises(HTTPException):
        srv.criar(db, saiu, "Algo", 12)


def test_resumo_ignora_concluidas_e_pacientes_que_sairam(db):
    p = paciente(db)
    vencida = srv.criar(db, p, "A", 12)
    vencida.vence_em = models.agora() - timedelta(hours=1)
    srv.criar(db, p, "B", 24)
    feita = srv.criar(db, p, "C", 12)
    srv.concluir(db, feita)
    outra = paciente(db, 2)
    srv.criar(db, outra, "D", 12)
    outra.status = "saiu"
    db.commit()
    assert srv.resumo(db, models.agora()) == {"vencidas": 1, "proximas": 0, "em_dia": 1}