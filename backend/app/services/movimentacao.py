"""Regras de movimentação das pacientes: alocar/mover, parto, saída e sinalizações."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models

FUSO_LOCAL_EM_HORAS = 3  # Pernambuco é UTC-3; o banco guarda UTC
PERFIS = {"gestante", "puerpera", "abortamento"}
TIPOS_PARTO = {"normal", "cesarea", "forceps"}
NASCIMENTOS = {"vivo", "natimorto"}
DESFECHOS = {"casa", "alojamento", "transferencia"}


class RegraErro(HTTPException):
    """Erro de regra de negócio: vira resposta HTTP com a mensagem exibida na tela."""

    def __init__(self, mensagem: str, status: int = 409):
        super().__init__(status_code=status, detail=mensagem)


def data_ou_agora(texto: str | None) -> datetime:
    """Converte '2026-11-16T14:30' (hora local) para UTC. Vazio = agora."""
    agora = models.agora()
    if not texto:
        return agora
    try:
        dt = datetime.fromisoformat(texto)
    except ValueError:
        raise RegraErro("Data/hora inválida.", 422)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        dt = dt + timedelta(hours=FUSO_LOCAL_EM_HORAS)
    if dt > agora + timedelta(minutes=5):
        raise RegraErro("A data/hora não pode estar no futuro.", 422)
    return dt


def ocupante(db: Session, localizacao_id: int):
    return (
        db.query(models.Paciente)
        .filter(models.Paciente.status == "ativa", models.Paciente.localizacao_id == localizacao_id)
        .first()
    )


def _liberar(local):
    """Quando a paciente sai de um local: leito vai para limpeza, maca deixa de existir."""
    if local is None:
        return
    if local.tipo == "leito":
        local.situacao = "limpeza"
    elif local.tipo == "maca":
        local.ativa = False


def _nova_maca(db: Session, descricao: str | None):
    existentes = {l.codigo for l in db.query(models.Localizacao).filter(models.Localizacao.tipo == "maca")}
    n = 1
    while f"M{n}" in existentes:
        n += 1
    maca = models.Localizacao(codigo=f"M{n}", tipo="maca", nome=f"Maca {n}", descricao=(descricao or "").strip() or None)
    db.add(maca)
    db.flush()
    return maca


def alocar(db: Session, paciente, codigo: str, data_hora=None, observacao=None, local_maca=None):
    if paciente.status != "ativa":
        raise RegraErro("A paciente já saiu do COB.")
    quando = data_ou_agora(data_hora)
    origem = paciente.localizacao

    if codigo == "NOVA_MACA":
        destino = _nova_maca(db, local_maca)
    else:
        destino = db.query(models.Localizacao).filter_by(codigo=codigo, ativa=True).first()
        if destino is None:
            raise RegraErro("Local não encontrado.", 404)
        if origem is not None and destino.id == origem.id:
            raise RegraErro("A paciente já está neste local.")
        if destino.situacao == "indisponivel":
            raise RegraErro(f"{destino.nome} está indisponível.")
        if destino.situacao == "limpeza":
            raise RegraErro(f"{destino.nome} está em limpeza. Libere o leito antes.")
        outra = ocupante(db, destino.id)
        if outra is not None and outra.id != paciente.id:
            raise RegraErro(f"{destino.nome} já está ocupado por {outra.nome}.")

    _liberar(origem)
    paciente.localizacao_id = destino.id
    db.add(models.Movimentacao(
        paciente_id=paciente.id,
        origem_id=origem.id if origem else None,
        destino_id=destino.id,
        motivo="alocacao" if origem is None else "movimentacao",
        data_hora=quando,
        observacao=(observacao or "").strip() or None,
    ))
    db.commit()
    return destino


def registrar_parto(db: Session, paciente, tipo: str, nascimento: str, data_hora=None):
    if paciente.status != "ativa":
        raise RegraErro("A paciente já saiu do COB.")
    if paciente.parto is not None:
        raise RegraErro("O parto desta paciente já foi registrado.")
    if tipo not in TIPOS_PARTO or nascimento not in NASCIMENTOS:
        raise RegraErro("Tipo de parto ou nascimento inválido.", 422)
    db.add(models.Parto(paciente_id=paciente.id, data_hora=data_ou_agora(data_hora), tipo=tipo, nascimento=nascimento))
    paciente.parindo = False
    paciente.perfil = "puerpera"
    db.commit()


def registrar_saida(db: Session, paciente, desfecho: str, data_hora=None):
    if paciente.status != "ativa":
        raise RegraErro("A paciente já saiu do COB.")
    if desfecho not in DESFECHOS:
        raise RegraErro("Desfecho inválido.", 422)
    quando = data_ou_agora(data_hora)
    origem = paciente.localizacao
    _liberar(origem)
    db.add(models.Movimentacao(
        paciente_id=paciente.id,
        origem_id=origem.id if origem else None,
        destino_id=None,
        motivo="saida",
        data_hora=quando,
        observacao=f"Desfecho: {desfecho}",
    ))
    paciente.status = "saiu"
    paciente.desfecho = desfecho
    paciente.saida_em = quando
    paciente.localizacao_id = None
    db.commit()


def atualizar_sinalizacoes(db: Session, paciente, dados: dict):
    if "perfil" in dados and dados["perfil"] is not None:
        if dados["perfil"] not in PERFIS:
            raise RegraErro("Perfil inválido.", 422)
        paciente.perfil = dados["perfil"]
    for campo in ("parindo", "comorbidade", "atb", "reserva_sanguinea", "tarh"):
        if dados.get(campo) is not None:
            setattr(paciente, campo, bool(dados[campo]))
    if "alergia" in dados:
        paciente.alergia = (dados["alergia"] or "").strip() or None
    if "bolsa_rota_horas" in dados:
        h = dados["bolsa_rota_horas"]
        if h is not None and not (0 <= h <= 240):
            raise RegraErro("Horas de bolsa rota inválidas.", 422)
        paciente.bolsa_rota_em = None if h is None else models.agora() - timedelta(hours=h)
    db.commit()