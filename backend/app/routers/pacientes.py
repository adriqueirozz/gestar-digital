from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.services import movimentacao
from app.services import pendencias as srv_pend
from app.services.movimentacao import RegraErro

router = APIRouter(prefix="/pacientes", tags=["pacientes"])


class AlocacaoIn(BaseModel):
    destino: str                      # código do local ou "NOVA_MACA"
    data_hora: str | None = None      # '2026-11-16T14:30' (hora local)
    observacao: str | None = None
    local_maca: str | None = None


class PartoIn(BaseModel):
    tipo: str                         # normal | cesarea | forceps
    nascimento: str                   # vivo | natimorto
    data_hora: str | None = None


class SaidaIn(BaseModel):
    desfecho: str                     # casa | alojamento | transferencia
    data_hora: str | None = None


class SinalizacoesIn(BaseModel):
    perfil: str | None = None
    parindo: bool | None = None
    comorbidade: bool | None = None
    atb: bool | None = None
    reserva_sanguinea: bool | None = None
    tarh: bool | None = None
    alergia: str | None = None
    bolsa_rota_horas: int | None = None   # None = sem bolsa rota


def _iso(dt):
    return dt.isoformat() + "Z" if dt else None  # banco guarda UTC


def _horas(inicio, agora):
    return (agora - inicio).total_seconds() / 3600


def _paciente(db: Session, paciente_id: int):
    p = db.get(models.Paciente, paciente_id)
    if p is None:
        raise RegraErro("Paciente não encontrada.", 404)
    return p


def _detalhe(db: Session, p) -> dict:
    agora = models.agora()
    locais = {l.id: l for l in db.query(models.Localizacao).all()}
    nome = lambda i: locais[i].nome if i in locais else None
    historico = sorted(p.movimentacoes, key=lambda m: (m.data_hora, m.id), reverse=True)
    loc = locais.get(p.localizacao_id)
    gpa = f"G{p.gestas}P{p.partos}A{p.abortos}" if None not in (p.gestas, p.partos, p.abortos) else None
    ig = None
    if p.ig_semanas is not None:
        ig = f"{p.ig_semanas}s" + (f"{p.ig_dias}d" if p.ig_dias is not None else "")
    return {
        "id": p.id, "nome": p.nome, "prontuario": p.prontuario, "status": p.status,
        "perfil": p.perfil, "gpa": gpa, "ig": ig,
        "diagnostico": p.diagnostico, "observacoes": p.observacoes_origem,
        "chegada_em": _iso(p.chegada_em), "chegada_tem_hora": p.chegada_tem_hora,
        "espera_min": int(_horas(p.chegada_em, agora) * 60) if p.chegada_tem_hora and p.status == "ativa" else None,
        "parindo": p.parindo, "comorbidade": p.comorbidade, "atb": p.atb,
        "reserva_sanguinea": p.reserva_sanguinea, "tarh": p.tarh, "alergia": p.alergia,
        "bolsa_rota_horas": int(_horas(p.bolsa_rota_em, agora)) if p.bolsa_rota_em else None,
        "localizacao": {"codigo": loc.codigo, "nome": loc.nome, "tipo": loc.tipo} if loc else None,
        "parto": {"data_hora": _iso(p.parto.data_hora), "tipo": p.parto.tipo, "nascimento": p.parto.nascimento,
                  "horas": int(_horas(p.parto.data_hora, agora))} if p.parto else None,
        "desfecho": p.desfecho, "saida_em": _iso(p.saida_em),
        "pendencias": [srv_pend.serializar(x, agora) for x in sorted(p.pendencias, key=lambda y: y.vence_em)
                       if not x.concluida_em],
        "historico": [
            {"data_hora": _iso(m.data_hora), "motivo": m.motivo, "origem": nome(m.origem_id),
             "destino": nome(m.destino_id), "observacao": m.observacao}
            for m in historico
        ],
    }


@router.get("/{paciente_id}")
def detalhe(paciente_id: int, db: Session = Depends(get_db)):
    return _detalhe(db, _paciente(db, paciente_id))


@router.post("/{paciente_id}/alocar")
def alocar(paciente_id: int, corpo: AlocacaoIn, db: Session = Depends(get_db)):
    p = _paciente(db, paciente_id)
    destino = movimentacao.alocar(db, p, corpo.destino, corpo.data_hora, corpo.observacao, corpo.local_maca)
    return {"ok": True, "destino": destino.codigo}


@router.post("/{paciente_id}/parto")
def parto(paciente_id: int, corpo: PartoIn, db: Session = Depends(get_db)):
    movimentacao.registrar_parto(db, _paciente(db, paciente_id), corpo.tipo, corpo.nascimento, corpo.data_hora)
    return {"ok": True}


@router.post("/{paciente_id}/saida")
def saida(paciente_id: int, corpo: SaidaIn, db: Session = Depends(get_db)):
    movimentacao.registrar_saida(db, _paciente(db, paciente_id), corpo.desfecho, corpo.data_hora)
    return {"ok": True}


@router.patch("/{paciente_id}/sinalizacoes")
def sinalizacoes(paciente_id: int, corpo: SinalizacoesIn, db: Session = Depends(get_db)):
    movimentacao.atualizar_sinalizacoes(db, _paciente(db, paciente_id), corpo.model_dump(exclude_unset=True))
    return {"ok": True}