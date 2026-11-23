from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import editor, id_de, usuario_atual
from app.database import get_db
from app.services import exportacao as srv

router = APIRouter(prefix="/exportacoes", tags=["exportacoes"])


@router.get("/planilha")
def baixar_planilha(db: Session = Depends(get_db), usuario=Depends(editor)):
    """Gera o CSV no formato da planilha, registra a exportação e entrega o arquivo."""
    conteudo = srv.gerar_csv(db)
    nome = srv.nome_arquivo()
    srv.registrar(db, nome, id_de(usuario))  # só registra depois de gerar com sucesso
    return StreamingResponse(
        iter([conteudo.encode("utf-8-sig")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/ultima", dependencies=[Depends(usuario_atual)])
def ultima_exportacao(db: Session = Depends(get_db)):
    """Data/hora da última exportação (ou null se nunca exportou)."""
    return srv.ultima(db)