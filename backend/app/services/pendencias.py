"""Regras de pendências com prazo de 12h ou 24h."""
from datetime import timedelta

from sqlalchemy.orm import Session

from app import models
from app.services.movimentacao import RegraErro

PRAZOS = {12, 24}
LIMITE_PROXIMA_MIN = 180  # "próxima do vencimento" = falta 3h ou menos


def iso(dt):
    return dt.isoformat() + "Z" if dt else None  # banco guarda UTC


def situacao(pend, agora) -> str:
    """concluida | vencida | proxima | em_dia"""
    if pend.concluida_em:
        return "concluida"
    restante_min = int((pend.vence_em - agora).total_seconds() / 60)
    if restante_min < 0:
        return "vencida"
    if restante_min <= LIMITE_PROXIMA_MIN:
        return "proxima"
    return "em_dia"


def serializar(pend, agora) -> dict:
    return {
        "id": pend.id,
        "paciente_id": pend.paciente_id,
        "descricao": pend.descricao,
        "prazo_horas": pend.prazo_horas,
        "criada_em": iso(pend.criada_em),
        "vence_em": iso(pend.vence_em),
        "restante_min": int((pend.vence_em - agora).total_seconds() / 60),
        "status": situacao(pend, agora),
        "concluida_em": iso(pend.concluida_em),
        "criada_por": pend.criada_por.nome if pend.criada_por else None,
        "concluida_por": pend.concluida_por.nome if pend.concluida_por else None,
    }


def criar(db: Session, paciente, descricao: str, prazo_horas: int, usuario_id=None):
    texto = (descricao or "").strip()
    if not texto:
        raise RegraErro("Escreva a descrição da pendência.", 422)
    if len(texto) > 200:
        raise RegraErro("A descrição pode ter no máximo 200 caracteres.", 422)
    if prazo_horas not in PRAZOS:
        raise RegraErro("O prazo deve ser de 12 ou 24 horas.", 422)
    if paciente.status != "ativa":
        raise RegraErro("A paciente já saiu do COB.")
    criada = models.agora()
    pend = models.Pendencia(
        paciente_id=paciente.id, descricao=texto, prazo_horas=prazo_horas,
        criada_em=criada, vence_em=criada + timedelta(hours=prazo_horas), criada_por_id=usuario_id,
    )
    db.add(pend)
    db.commit()
    return pend


def concluir(db: Session, pend, usuario_id=None):
    if pend.concluida_em:
        raise RegraErro("Esta pendência já foi concluída.")
    pend.concluida_em = models.agora()
    pend.concluida_por_id = usuario_id
    db.commit()
    return pend


def abertas(db: Session):
    """Pendências não concluídas de pacientes que ainda estão no COB."""
    return (
        db.query(models.Pendencia)
        .join(models.Paciente, models.Pendencia.paciente_id == models.Paciente.id)
        .filter(models.Paciente.status == "ativa", models.Pendencia.concluida_em.is_(None))
        .all()
    )


def resumo(db: Session, agora) -> dict:
    contagem = {"vencidas": 0, "proximas": 0, "em_dia": 0}
    chave = {"vencida": "vencidas", "proxima": "proximas", "em_dia": "em_dia"}
    for pend in abertas(db):
        contagem[chave[situacao(pend, agora)]] += 1
    return contagem