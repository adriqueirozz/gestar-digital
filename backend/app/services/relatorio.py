
import calendar
import csv
import io
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models


FUSO_LOCAL_EM_HORAS = 3


def periodo_mes(mes: str):
    """Recebe AAAA-MM e devolve os limites do mês em UTC."""
    try:
        ano, numero_mes = map(int, mes.split("-"))

        if numero_mes < 1 or numero_mes > 12:
            raise ValueError

        inicio_local = datetime(ano, numero_mes, 1)

        if numero_mes == 12:
            fim_local = datetime(ano + 1, 1, 1)
        else:
            fim_local = datetime(ano, numero_mes + 1, 1)

    except (ValueError, AttributeError):
        raise ValueError("Informe o mês no formato AAAA-MM.")

    inicio = inicio_local + timedelta(hours=FUSO_LOCAL_EM_HORAS)
    fim = fim_local + timedelta(hours=FUSO_LOCAL_EM_HORAS)

    return inicio, fim


def calcular_relatorio(db: Session, mes: str):
    inicio, fim = periodo_mes(mes)
    agora = models.agora()

    # Atendimentos iniciados no mês
    atendidas = (
        db.query(models.Paciente)
        .filter(
            models.Paciente.chegada_em >= inicio,
            models.Paciente.chegada_em < fim,
        )
        .all()
    )

    total_atendidas = len(atendidas)

    # Pacientes desse período que continuam internadas
    internadas = sum(1 for p in atendidas if p.status == "ativa")

    # Saídas registradas no período
    saidas = (
        db.query(models.Paciente)
        .filter(
            models.Paciente.saida_em >= inicio,
            models.Paciente.saida_em < fim,
        )
        .all()
    )

    altas = sum(1 for p in saidas if p.desfecho == "casa")
    transferencias = sum(
        1 for p in saidas if p.desfecho == "transferencia"
    )
    alojamento = sum(
        1 for p in saidas if p.desfecho == "alojamento"
    )

    # Partos registrados no período
    partos = (
        db.query(models.Parto)
        .filter(
            models.Parto.data_hora >= inicio,
            models.Parto.data_hora < fim,
        )
        .all()
    )

    total_partos = len(partos)

    parto_normal = sum(
        1 for p in partos if p.tipo == "normal"
    )

    cesareas = sum(
        1 for p in partos if p.tipo == "cesarea"
    )

    # Natimortos (óbitos fetais). Óbito neonatal (após nascer vivo) não é registrado no sistema.
    obitos_neonatais = sum(
        1 for p in partos if p.nascimento == "natimorto"
    )

    # O sistema não possui campo de óbito materno.
    obitos_maternos = None

    # Permanência média das pacientes que saíram no período
    permanencias = [
        (p.saida_em - p.chegada_em).total_seconds() / 3600
        for p in saidas
        if p.saida_em and p.chegada_em
        and p.saida_em >= p.chegada_em
    ]

    permanencia_media = (
        round(sum(permanencias) / len(permanencias), 1)
        if permanencias else None
    )

    # Ocupação atual dos leitos
    leitos = (
        db.query(models.Localizacao)
        .filter(
            models.Localizacao.tipo == "leito",
            models.Localizacao.ativa.is_(True),
        )
        .all()
    )

    leitos_disponiveis = [
        l for l in leitos if l.situacao != "indisponivel"
    ]

    ocupados = (
        db.query(models.Paciente)
        .join(
            models.Localizacao,
            models.Paciente.localizacao_id == models.Localizacao.id,
        )
        .filter(
            models.Paciente.status == "ativa",
            models.Localizacao.tipo == "leito",
        )
        .count()
    )

    total_leitos = len(leitos_disponiveis)

    ocupacao_atual = (
        round(ocupados / total_leitos * 100)
        if total_leitos else 0
    )

    # Pacientes atualmente alocadas em macas
    pacientes_maca = (
        db.query(models.Paciente)
        .join(
            models.Localizacao,
            models.Paciente.localizacao_id == models.Localizacao.id,
        )
        .filter(
            models.Paciente.status == "ativa",
            models.Localizacao.tipo == "maca",
        )
        .all()
    )

    total_macas = len(pacientes_maca)

    esperas = [
        (agora - p.chegada_em).total_seconds() / 60
        for p in pacientes_maca
        if p.chegada_tem_hora and p.chegada_em <= agora
    ]

    espera_media = (
        round(sum(esperas) / len(esperas))
        if esperas else None
    )

    return {
        "mes": mes,
        "atendimentos": {
            "atendidas": total_atendidas,
            "internadas": internadas,
        },
        "saidas": {
            "altas": altas,
            "transferencias": transferencias,
            "alojamento": alojamento,
        },
        "nascimentos": {
            "total": total_partos,
            "normal": parto_normal,
            "cesarea": cesareas,
        },
        "obitos": {
            "neonatais": obitos_neonatais,
            "maternos": obitos_maternos,
        },
        "permanencia": {
            "media_horas": permanencia_media,
            "ocupacao_atual": ocupacao_atual,
            "leitos_ocupados": ocupados,
            "leitos_disponiveis": total_leitos,
        },
        "macas": {
            "atendidas": total_macas,
            "espera_media_minutos": espera_media,
        },
    }


def dados_csv(relatorio: dict):
    linhas = [
        ("Atendidas", relatorio["atendimentos"]["atendidas"]),
        ("Internadas atualmente", relatorio["atendimentos"]["internadas"]),
        ("Altas", relatorio["saidas"]["altas"]),
        ("Transferências", relatorio["saidas"]["transferencias"]),
        ("Alojamento conjunto", relatorio["saidas"]["alojamento"]),
        ("Nascimentos", relatorio["nascimentos"]["total"]),
        ("Parto vaginal", relatorio["nascimentos"]["normal"]),
        ("Cesáreas", relatorio["nascimentos"]["cesarea"]),
        ("Natimortos", relatorio["obitos"]["neonatais"]),
        ("Óbitos maternos", "Não disponível"),
        ("Permanência média (horas)", relatorio["permanencia"]["media_horas"]),
        ("Ocupação atual (%)", relatorio["permanencia"]["ocupacao_atual"]),
        ("Pacientes em maca", relatorio["macas"]["atendidas"]),
        ("Espera média em maca (min)", relatorio["macas"]["espera_media_minutos"]),
    ]

    return linhas


def gerar_csv(relatorio: dict):
    arquivo = io.StringIO()
    escritor = csv.writer(arquivo, delimiter=";")

    escritor.writerow(["Métrica", "Valor"])

    for metrica, valor in dados_csv(relatorio):
        escritor.writerow([metrica, valor if valor is not None else "Não disponível"])

    return "\ufeff" + arquivo.getvalue()


def gerar_pdf(relatorio: dict):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    )

    arquivo = io.BytesIO()

    documento = SimpleDocTemplate(
        arquivo,
        pagesize=A4,
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    estilos = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "TituloGestar",
        parent=estilos["Title"],
        fontSize=20,
        textColor=colors.HexColor("#292929"),
        alignment=TA_CENTER,
        spaceAfter=6,
    )

    subtitulo = ParagraphStyle(
        "SubtituloGestar",
        parent=estilos["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#777777"),
        alignment=TA_CENTER,
        spaceAfter=20,
    )

    conteudo = [
        Paragraph("GESTAR DIGITAL", titulo),
        Paragraph(
            f"Relatório mensal · {relatorio['mes']}",
            subtitulo,
        ),
    ]

    indicadores = [
        ["Indicador", "Quantidade"],
        ["Atendimentos", relatorio["atendimentos"]["atendidas"]],
        ["Internadas atualmente", relatorio["atendimentos"]["internadas"]],
        ["Altas", relatorio["saidas"]["altas"]],
        ["Transferências", relatorio["saidas"]["transferencias"]],
        ["Alojamento conjunto", relatorio["saidas"]["alojamento"]],
        ["Nascimentos", relatorio["nascimentos"]["total"]],
        ["Parto vaginal", relatorio["nascimentos"]["normal"]],
        ["Cesáreas", relatorio["nascimentos"]["cesarea"]],
        ["Natimortos", relatorio["obitos"]["neonatais"]],
        ["Óbitos maternos", "Não disponível"],
        [
            "Permanência média (horas)",
            relatorio["permanencia"]["media_horas"] or "—",
        ],
        [
            "Ocupação atual (%)",
            relatorio["permanencia"]["ocupacao_atual"],
        ],
        ["Pacientes em maca", relatorio["macas"]["atendidas"]],
        [
            "Espera média em maca (min)",
            relatorio["macas"]["espera_media_minutos"] or "—",
        ],
    ]

    tabela = Table(indicadores, colWidths=[11 * cm, 5 * cm])

    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#292929")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white, colors.HexColor("#f4f4f4")
        ]),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 1), (1, -1), "CENTER"),
    ]))

    conteudo.extend([
        tabela,
        Spacer(1, 18),
        Paragraph(
            "Documento gerado automaticamente pelo Gestar Digital. "
            "Os indicadores refletem os registros disponíveis no sistema.",
            estilos["Italic"],
        ),
    ])

    documento.build(conteudo)

    arquivo.seek(0)
    return arquivo
