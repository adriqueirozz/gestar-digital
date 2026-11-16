from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.services.movimentacao import RegraErro, ocupante

router = APIRouter(prefix="/locais", tags=["locais"])

SITUACOES = {"normal", "limpeza", "indisponivel"}


class SituacaoIn(BaseModel):
    situacao: str


class MacaIn(BaseModel):
    descricao: str


def _local(db: Session, codigo: str):
    local = db.query(models.Localizacao).filter_by(codigo=codigo, ativa=True).first()
    if local is None:
        raise RegraErro("Local não encontrado.", 404)
    return local


@router.get("/destinos")
def destinos(db: Session = Depends(get_db)):
    """Locais livres e utilizáveis, para o modal Alocar / mover."""
    ativos = db.query(models.Paciente).filter(models.Paciente.status == "ativa").all()
    ocupados = {p.localizacao_id for p in ativos if p.localizacao_id}
    locais = (
        db.query(models.Localizacao)
        .filter(models.Localizacao.ativa.is_(True), models.Localizacao.situacao == "normal")
        .order_by(models.Localizacao.codigo)
        .all()
    )
    livres = [l for l in locais if l.id not in ocupados]

    def por_tipo(tipo):
        return [{"codigo": l.codigo, "nome": l.nome} for l in livres if l.tipo == tipo]

    return {
        "leitos": por_tipo("leito"),
        "salas_parto": por_tipo("sala_parto"),
        "salas_cirurgia": por_tipo("centro_cirurgico"),
        "apoio": por_tipo("apoio"),
    }


@router.post("/{codigo}/situacao")
def mudar_situacao(codigo: str, corpo: SituacaoIn, db: Session = Depends(get_db)):
    local = _local(db, codigo)
    if local.tipo != "leito":
        raise RegraErro("Só leitos têm situação (livre, limpeza, indisponível).", 422)
    if corpo.situacao not in SITUACOES:
        raise RegraErro("Situação inválida.", 422)
    if corpo.situacao != "normal" and ocupante(db, local.id) is not None:
        raise RegraErro("O leito está ocupado. Mova a paciente ou registre a saída antes.")
    local.situacao = corpo.situacao
    db.commit()
    return {"codigo": local.codigo, "situacao": local.situacao}


@router.patch("/{codigo}")
def editar_maca(codigo: str, corpo: MacaIn, db: Session = Depends(get_db)):
    local = _local(db, codigo)
    if local.tipo != "maca":
        raise RegraErro("Só macas têm local editável.", 422)
    local.descricao = corpo.descricao.strip() or None
    db.commit()
    return {"codigo": local.codigo, "descricao": local.descricao}