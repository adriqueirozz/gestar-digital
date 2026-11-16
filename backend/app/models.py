from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import JSON 
from app.database import Base


def agora() -> datetime:
    """Data/hora atual em UTC, sem fuso (como o SQLite guarda)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    login: Mapped[str] = mapped_column(String(50), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[str] = mapped_column(String(20))  # enfermagem | medico | gestao
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Localizacao(Base):
    __tablename__ = "localizacoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)  # E3A, PN1, CC1, USG, M1
    tipo: Mapped[str] = mapped_column(String(20))  # leito | maca | sala_parto | centro_cirurgico | apoio
    nome: Mapped[str] = mapped_column(String(80))
    enfermaria: Mapped[int | None] = mapped_column(Integer)  # 1 a 9, só para leitos
    situacao: Mapped[str] = mapped_column(String(20), default="normal")  # normal | limpeza | indisponivel
    descricao: Mapped[str | None] = mapped_column(String(120))  # local da maca (corredor...)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)  # maca removida = False


class Importacao(Base):
    __tablename__ = "importacoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime, default=agora)
    origem: Mapped[str] = mapped_column(String(20))  # csv | excel | graph
    arquivo: Mapped[str | None] = mapped_column(String(255))
    linhas_lidas: Mapped[int] = mapped_column(Integer, default=0)
    linhas_com_problema: Mapped[int] = mapped_column(Integer, default=0)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))


class ImportacaoProblema(Base):
    __tablename__ = "importacao_problemas"
    id: Mapped[int] = mapped_column(primary_key=True)
    importacao_id: Mapped[int] = mapped_column(ForeignKey("importacoes.id"))
    linha: Mapped[int] = mapped_column(Integer)
    valor: Mapped[str | None] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(40))  # leito_nao_reconhecido | campo_vazio | divergencia
    detalhe: Mapped[str | None] = mapped_column(Text)
    resolvido: Mapped[bool] = mapped_column(Boolean, default=False)


class Paciente(Base):
    __tablename__ = "pacientes"
    id: Mapped[int] = mapped_column(primary_key=True)

    # --- dados de ORIGEM (planilha): somente leitura no Gestar ---
    prontuario: Mapped[str | None] = mapped_column(String(30), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(120))
    gestas: Mapped[int | None] = mapped_column(Integer)
    partos: Mapped[int | None] = mapped_column(Integer)
    abortos: Mapped[int | None] = mapped_column(Integer)
    ig_semanas: Mapped[int | None] = mapped_column(Integer)
    ig_dias: Mapped[int | None] = mapped_column(Integer)
    diagnostico: Mapped[str | None] = mapped_column(Text)
    observacoes_origem: Mapped[str | None] = mapped_column(Text)
    chegada_em: Mapped[datetime] = mapped_column(DateTime)
    chegada_tem_hora: Mapped[bool] = mapped_column(Boolean, default=True)
    linha_origem: Mapped[int | None] = mapped_column(Integer)      # nº da linha na planilha
    leito_origem: Mapped[str | None] = mapped_column(String(60))   # texto original ("Enf 3 - Leito A")
    dados_origem: Mapped[dict | None] = mapped_column(JSON)        # linha completa, com todas as colunas
    importacao_id: Mapped[int | None] = mapped_column(ForeignKey("importacoes.id"))

    # --- dados do GESTAR: a reimportação nunca sobrescreve ---
    perfil: Mapped[str] = mapped_column(String(20), default="gestante")  # gestante | puerpera | abortamento
    parindo: Mapped[bool] = mapped_column(Boolean, default=False)
    comorbidade: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="ativa", index=True)  # ativa | saiu
    localizacao_id: Mapped[int | None] = mapped_column(ForeignKey("localizacoes.id"), index=True)  # None = fila
    bolsa_rota_em: Mapped[datetime | None] = mapped_column(DateTime)
    atb: Mapped[bool] = mapped_column(Boolean, default=False)
    reserva_sanguinea: Mapped[bool] = mapped_column(Boolean, default=False)
    tarh: Mapped[bool] = mapped_column(Boolean, default=False)
    alergia: Mapped[str | None] = mapped_column(String(120))
    desfecho: Mapped[str | None] = mapped_column(String(20))  # casa | alojamento | transferencia
    saida_em: Mapped[datetime | None] = mapped_column(DateTime)

    localizacao: Mapped["Localizacao | None"] = relationship()
    parto: Mapped["Parto | None"] = relationship(back_populates="paciente")
    movimentacoes: Mapped[list["Movimentacao"]] = relationship(back_populates="paciente")
    pendencias: Mapped[list["Pendencia"]] = relationship(back_populates="paciente")

class Parto(Base):
    __tablename__ = "partos"
    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"), unique=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime, default=agora)
    tipo: Mapped[str] = mapped_column(String(20))  # normal | cesarea | forceps
    nascimento: Mapped[str] = mapped_column(String(20))  # vivo | natimorto
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    paciente: Mapped["Paciente"] = relationship(back_populates="parto")


class Movimentacao(Base):
    __tablename__ = "movimentacoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"))
    origem_id: Mapped[int | None] = mapped_column(ForeignKey("localizacoes.id"))
    destino_id: Mapped[int | None] = mapped_column(ForeignKey("localizacoes.id"))  # None = saiu do COB
    motivo: Mapped[str] = mapped_column(String(20))  # alocacao | movimentacao | saida
    data_hora: Mapped[datetime] = mapped_column(DateTime, default=agora)
    observacao: Mapped[str | None] = mapped_column(String(255))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    paciente: Mapped["Paciente"] = relationship(back_populates="movimentacoes")


class Pendencia(Base):
    __tablename__ = "pendencias"
    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"))
    descricao: Mapped[str] = mapped_column(String(200))
    prazo_horas: Mapped[int] = mapped_column(Integer)  # 12 ou 24
    criada_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
    vence_em: Mapped[datetime] = mapped_column(DateTime)
    criada_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    concluida_em: Mapped[datetime | None] = mapped_column(DateTime)
    concluida_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    paciente: Mapped["Paciente"] = relationship(back_populates="pendencias")


class Exportacao(Base):
    __tablename__ = "exportacoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime, default=agora)
    arquivo: Mapped[str | None] = mapped_column(String(255))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))


class Configuracao(Base):
    __tablename__ = "configuracoes"
    chave: Mapped[str] = mapped_column(String(50), primary_key=True)  # ex.: limite_lotacao
    valor: Mapped[str] = mapped_column(String(100))


class Auditoria(Base):
    """Criada agora, preenchida no G-20 (quem alterou cada informação)."""
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(primary_key=True)
    entidade: Mapped[str] = mapped_column(String(40))
    entidade_id: Mapped[int] = mapped_column(Integer)
    campo: Mapped[str] = mapped_column(String(60))
    valor_antigo: Mapped[str | None] = mapped_column(String(255))
    valor_novo: Mapped[str | None] = mapped_column(String(255))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    data_hora: Mapped[datetime] = mapped_column(DateTime, default=agora)