from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.services import importacao

router = APIRouter(prefix="/importacoes", tags=["importacoes"])


@router.post("")
async def enviar_planilha(arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    """Recebe um .csv ou .xlsx, importa as pacientes e devolve o resumo com os problemas encontrados."""
    conteudo = await arquivo.read()
    try:
        return importacao.importar(db, conteudo, arquivo.filename or "planilha.csv")
    except ValueError as erro:  # coluna faltando, formato não suportado...
        raise HTTPException(status_code=400, detail=str(erro))


@router.get("/ultima")
def ultima_importacao(db: Session = Depends(get_db)):
    """Resumo da última importação (usado na tela de conferência). Devolve null se ainda não houve."""
    ultima = db.query(models.Importacao).order_by(models.Importacao.id.desc()).first()
    if ultima is None:
        return None
    return {"importacao_id": ultima.id, "arquivo": ultima.arquivo, "data_hora": ultima.data_hora,
            "linhas_lidas": ultima.linhas_lidas, "linhas_com_problema": ultima.linhas_com_problema,
            "problemas": importacao.listar_problemas(db, ultima.id)}