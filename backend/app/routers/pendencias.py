from datetime import timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.auth import editor, id_de
from app.database import get_db
from app.routers.painel import _tags
from app.services import pendencias as srv
from app.services.movimentacao import RegraErro

router = APIRouter(prefix="/pendencias", tags=["pendencias"])

RANK_TIPO = {"leito": 0, "sala_parto": 1, "centro_cirurgico": 1, "apoio": 2, "maca": 3}
CHAVE_RESUMO = {"vencida": "vencidas", "proxima": "proximas", "em_dia": "em_dia", "concluida": "concluidas"}


class PendenciaIn(BaseModel):
    paciente_id: int
    descricao: str
    prazo_horas: int  # 12 ou 24


def _grupo(loc) -> str:
    if loc is None:
        return "Aguardando alocação"
    if loc.tipo == "leito":
        return f"Enfermaria {loc.enfermaria}"
    if loc.tipo in ("sala_parto", "centro_cirurgico"):
        return "Salas"
    if loc.tipo == "apoio":
        return "Apoio"
    return "Macas e corredores"


@router.post("")
def criar(corpo: PendenciaIn, db: Session = Depends(get_db), usuario=Depends(editor)):
    paciente = db.get(models.Paciente, corpo.paciente_id)
    if paciente is None:
        raise RegraErro("Paciente não encontrada.", 404)
    pend = srv.criar(db, paciente, corpo.descricao, corpo.prazo_horas, usuario_id=id_de(usuario))
    return srv.serializar(pend, models.agora())


@router.post("/{pendencia_id}/concluir")
def concluir(pendencia_id: int, db: Session = Depends(get_db), usuario=Depends(editor)):
    pend = db.get(models.Pendencia, pendencia_id)
    if pend is None:
        raise RegraErro("Pendência não encontrada.", 404)
    return srv.serializar(srv.concluir(db, pend, usuario_id=id_de(usuario)), models.agora())


@router.get("/plantao")
def plantao(db: Session = Depends(get_db)):
    """Passagem de plantão: todas as pacientes no COB, agrupadas por local, com suas pendências."""
    agora = models.agora()
    limite = agora - timedelta(hours=12)  # concluídas há mais de 12h saem da lista
    resumo = {"vencidas": 0, "proximas": 0, "em_dia": 0, "concluidas": 0}
    lista = []

    for p in db.query(models.Paciente).filter(models.Paciente.status == "ativa").all():
        loc = p.localizacao
        pendencias = []
        for pend in sorted(p.pendencias, key=lambda x: x.vence_em):
            if pend.concluida_em and pend.concluida_em < limite:
                continue
            dados = srv.serializar(pend, agora)
            resumo[CHAVE_RESUMO[dados["status"]]] += 1
            pendencias.append(dados)

        gpa = f"G{p.gestas}P{p.partos}A{p.abortos}" if None not in (p.gestas, p.partos, p.abortos) else "—"
        ig = "—"
        if p.ig_semanas is not None:
            ig = f"{p.ig_semanas}s" + (f"{p.ig_dias}d" if p.ig_dias is not None else "")
        ordem = (RANK_TIPO.get(loc.tipo, 9) if loc else 5, loc.codigo if loc else "", p.nome)
        lista.append((ordem, {
            "id": p.id, "nome": p.nome, "perfil": p.perfil, "tags": _tags(p, agora),
            "gpa": gpa, "ig": ig, "diagnostico": p.diagnostico or "",
            "grupo": _grupo(loc), "local": loc.nome if loc else "Sem local",
            "pendencias": pendencias,
        }))

    lista.sort(key=lambda par: par[0])
    return {"resumo": resumo, "itens": [item for _, item in lista], "gerado_em": srv.iso(agora)}