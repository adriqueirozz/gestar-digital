
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import relatorio as servico


router = APIRouter(prefix="/relatorios", tags=["relatorios"])


def obter_relatorio(mes: str, db: Session):
    try:
        return servico.calcular_relatorio(db, mes)
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro))


@router.get("/mensal")
def relatorio_mensal(
    mes: str,
    db: Session = Depends(get_db),
):
    return obter_relatorio(mes, db)


@router.get("/mensal/csv")
def exportar_csv(
    mes: str,
    db: Session = Depends(get_db),
):
    dados = obter_relatorio(mes, db)
    conteudo = servico.gerar_csv(dados)

    return StreamingResponse(
        iter([conteudo.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="relatorio-{mes}.csv"'
        },
    )


@router.get("/mensal/pdf")
def exportar_pdf(
    mes: str,
    db: Session = Depends(get_db),
):
    dados = obter_relatorio(mes, db)
    arquivo = servico.gerar_pdf(dados)

    return StreamingResponse(
        arquivo,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="relatorio-{mes}.pdf"'
        },
    )
