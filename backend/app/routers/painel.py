from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.database import get_db

router = APIRouter(prefix="/painel", tags=["painel"])


@router.get("")
def painel(db: Session = Depends(get_db)):
    locais = db.query(models.Localizacao).filter(models.Localizacao.ativa.is_(True)).all()
    ativos = db.query(models.Paciente).filter(models.Paciente.status == "ativa").all()
    por_local = {p.localizacao_id: p for p in ativos if p.localizacao_id}

    def situacao(l):
        if l.situacao != "normal":
            return l.situacao
        return "ocupado" if l.id in por_local else "livre"

    enfermarias = {}
    for l in sorted((x for x in locais if x.tipo == "leito"), key=lambda x: x.codigo):
        p = por_local.get(l.id)
        enfermarias.setdefault(l.enfermaria, []).append({
            "codigo": l.codigo,
            "situacao": situacao(l),
            "paciente": {"nome": p.nome, "perfil": p.perfil} if p else None,
        })

    leitos = [l for l in locais if l.tipo == "leito"]
    total = sum(1 for l in leitos if l.situacao != "indisponivel")
    ocupados = sum(1 for l in leitos if situacao(l) == "ocupado")
    ids_maca = {l.id for l in locais if l.tipo == "maca"}
    agora = models.agora()

    return {
        "ocupacao": {"ocupados": ocupados, "total": total, "percentual": round(ocupados / total * 100) if total else 0},
        "sem_leito": sum(1 for p in ativos if p.localizacao_id in ids_maca),
        "enfermarias": [{"numero": n, "leitos": ls} for n, ls in sorted(enfermarias.items())],
        "fila": [
            {"nome": p.nome, "perfil": p.perfil,
             "espera_min": int((agora - p.chegada_em).total_seconds() // 60) if p.chegada_tem_hora else None}
            for p in sorted(ativos, key=lambda x: x.chegada_em) if p.localizacao_id is None
        ],
    }