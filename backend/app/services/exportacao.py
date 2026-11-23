"""Exportação da planilha de pacientes no formato da planilha de origem (G-13).

Mantém as colunas originais e acrescenta, no fim, as informações do Gestar:
localização atual, parto e saída.
"""
import csv
from datetime import timedelta
from io import StringIO

from sqlalchemy.orm import Session

from app import models
from app.services.importacao import FUSO_LOCAL_EM_HORAS
from app.services.pendencias import iso

COL_LOCAL = "Localização atual"
COL_PARTO = "Parto"
COL_SAIDA = "Saída"
COLUNAS_GESTAR = [COL_LOCAL, COL_PARTO, COL_SAIDA]

# Usadas quando a paciente não tem a linha original guardada (ex.: criada pelo seed)
COLUNAS_ORIGEM_PADRAO = ["Leito", "Prontuário", "Data de entrada no COB", "Nome completo",
                         "GPA", "IG", "Diagnóstico", "OBS"]


def formatar_data(dt, com_hora=True) -> str:
    """Data do banco (UTC) -> texto no horário local. None vira texto vazio."""
    if dt is None:
        return ""
    local = dt - timedelta(hours=FUSO_LOCAL_EM_HORAS)
    return local.strftime("%d/%m/%Y %H:%M" if com_hora else "%d/%m/%Y")


def _origem_a_partir_do_banco(p) -> dict:
    """Plano B: remonta as colunas originais com os campos da própria paciente."""
    gpa = f"G{p.gestas}P{p.partos}A{p.abortos}" if None not in (p.gestas, p.partos, p.abortos) else ""
    ig = ""
    if p.ig_semanas is not None:
        ig = f"{p.ig_semanas}s{p.ig_dias}d" if p.ig_dias is not None else str(p.ig_semanas)
    return {
        "Leito": p.leito_origem or "",
        "Prontuário": p.prontuario or "",
        "Data de entrada no COB": formatar_data(p.chegada_em, com_hora=p.chegada_tem_hora),
        "Nome completo": p.nome,
        "GPA": gpa,
        "IG": ig,
        "Diagnóstico": p.diagnostico or "",
        "OBS": p.observacoes_origem or "",
    }


def linha_exportacao(p) -> dict:
    """Uma paciente -> um dicionário {coluna: valor} pronto para virar linha do arquivo."""
    linha = dict(p.dados_origem) if p.dados_origem else _origem_a_partir_do_banco(p)

    # Localização: a fila ainda não tem local
    if p.localizacao:
        linha[COL_LOCAL] = p.localizacao.codigo
    else:
        linha[COL_LOCAL] = "Aguardando alocação" if p.status == "ativa" else ""

    # Parto
    if p.parto:
        linha[COL_PARTO] = f"{formatar_data(p.parto.data_hora)} - {p.parto.tipo} ({p.parto.nascimento})"
    else:
        linha[COL_PARTO] = ""

    # Saída
    if p.saida_em or p.desfecho:
        partes = [formatar_data(p.saida_em), p.desfecho or ""]
        linha[COL_SAIDA] = " - ".join(x for x in partes if x)
    else:
        linha[COL_SAIDA] = ""

    return linha


def gerar_csv(db: Session) -> str:
    pacientes = db.query(models.Paciente).all()
    # ordem da planilha original; quem não tem linha de origem vai para o fim
    pacientes.sort(key=lambda p: (p.linha_origem is None, p.linha_origem or 0, p.id))
    linhas = [linha_exportacao(p) for p in pacientes]

    colunas = []
    for linha in linhas:
        for c in linha:
            if c not in colunas and c not in COLUNAS_GESTAR:
                colunas.append(c)
    if not colunas:
        colunas = list(COLUNAS_ORIGEM_PADRAO)
    colunas += COLUNAS_GESTAR

    saida = StringIO()
    escritor = csv.DictWriter(saida, fieldnames=colunas, delimiter=";",
                              extrasaction="ignore", restval="", lineterminator="\r\n")
    escritor.writeheader()
    escritor.writerows(linhas)
    return saida.getvalue()


def nome_arquivo() -> str:
    hoje = models.agora() - timedelta(hours=FUSO_LOCAL_EM_HORAS)
    return f"planilha-gestar-{hoje:%Y-%m-%d}.csv"


def registrar(db: Session, arquivo: str, usuario_id=None) -> models.Exportacao:
    exportacao = models.Exportacao(arquivo=arquivo, usuario_id=usuario_id)
    db.add(exportacao)
    db.commit()
    return exportacao


def ultima(db: Session) -> dict | None:
    e = db.query(models.Exportacao).order_by(models.Exportacao.data_hora.desc(), models.Exportacao.id.desc()).first()
    if e is None:
        return None
    usuario = db.get(models.Usuario, e.usuario_id) if e.usuario_id else None
    return {"id": e.id, "data_hora": iso(e.data_hora), "arquivo": e.arquivo,
            "usuario": usuario.nome if usuario else None}