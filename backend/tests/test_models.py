from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.database import Base


def test_alocacao_e_historico():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        leito = models.Localizacao(codigo="E1A", tipo="leito", nome="Enf. 1 · Leito A", enfermaria=1)
        p = models.Paciente(nome="Paciente Teste", gestas=2, partos=1, abortos=0,
                            ig_semanas=39, ig_dias=2, diagnostico="TPP", chegada_em=models.agora())
        db.add_all([leito, p])
        db.commit()

        p.localizacao_id = leito.id
        db.add(models.Movimentacao(paciente_id=p.id, destino_id=leito.id, motivo="alocacao"))
        db.commit()

        assert p.localizacao.codigo == "E1A"
        assert len(p.movimentacoes) == 1