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


def mapa_saidas(db: Session):
    """
    Data de saída de cada paciente (id -> datetime, em UTC).
    Usa Movimentacao (motivo == "saida") e, quando existir,
    Paciente.saida_em tem prioridade.
    """
    saidas = {}

    movimentacoes = (
        db.query(models.Movimentacao)
        .filter(models.Movimentacao.motivo == "saida")
        .order_by(models.Movimentacao.data_hora.asc())
        .all()
    )

    for movimentacao in movimentacoes:
        saidas[movimentacao.paciente_id] = movimentacao.data_hora

    com_saida = (
        db.query(models.Paciente)
        .filter(models.Paciente.saida_em.isnot(None))
        .all()
    )

    for paciente in com_saida:
        saidas[paciente.id] = paciente.saida_em

    return saidas


def carregar_historico(db: Session, fim: datetime):
    """
    Histórico de destinos de cada paciente até `fim`
    (paciente_id -> [(data_hora, destino_id), ...], em ordem cronológica).
    Ignora movimentações de saída e sem destino.
    """
    historico = {}

    movimentacoes = (
        db.query(models.Movimentacao)
        .filter(models.Movimentacao.data_hora < fim)
        .order_by(models.Movimentacao.data_hora.asc())
        .all()
    )

    for movimentacao in movimentacoes:
        if movimentacao.motivo == "saida" or movimentacao.destino_id is None:
            continue

        historico.setdefault(movimentacao.paciente_id, []).append(
            (movimentacao.data_hora, movimentacao.destino_id)
        )

    return historico


def calcular_ocupacao_media(
    db: Session,
    mes: str,
    total_leitos: int,
    saidas_por_paciente: dict,
):
    """
    Média das ocupações diárias (fechamento de cada dia, 23:59:59 locais)
    considerando apenas pacientes que estavam em LEITO naquele instante.
    Retorna (ocupacao_media, leitos_ocupados_no_ultimo_dia).
    """
    ano, numero_mes = map(int, mes.split("-"))
    _, fim = periodo_mes(mes)

    agora = models.agora()
    agora_local = agora - timedelta(hours=FUSO_LOCAL_EM_HORAS)

    if total_leitos == 0:
        return None, 0

    # Não calcula ocupação de meses futuros.
    if (ano, numero_mes) > (agora_local.year, agora_local.month):
        return None, 0

    mes_atual = (ano, numero_mes) == (agora_local.year, agora_local.month)

    if mes_atual:
        ultimo_dia = agora_local.day
    else:
        ultimo_dia = calendar.monthrange(ano, numero_mes)[1]

    ids_leitos = {
        linha[0]
        for linha in (
            db.query(models.Localizacao.id)
            .filter(models.Localizacao.tipo == "leito")
            .all()
        )
    }

    pacientes = (
        db.query(models.Paciente)
        .filter(models.Paciente.chegada_em < fim)
        .all()
    )

    historico = carregar_historico(db, fim)

    def em_leito(paciente, instante):
        movimentos = historico.get(paciente.id)

        # Sem movimentações registradas: usa a localização atual.
        if not movimentos:
            return paciente.localizacao_id in ids_leitos

        destino = None
        for data_hora, destino_id in movimentos:
            if data_hora <= instante:
                destino = destino_id
            else:
                break

        return destino in ids_leitos

    ocupacoes_diarias = []
    ocupados_ultimo_dia = 0

    for dia in range(1, ultimo_dia + 1):
        if mes_atual and dia == agora_local.day:
            fechamento_utc = agora
        else:
            fechamento_local = datetime(ano, numero_mes, dia, 23, 59, 59)
            fechamento_utc = fechamento_local + timedelta(
                hours=FUSO_LOCAL_EM_HORAS
            )

        ocupados = 0

        for paciente in pacientes:
            if paciente.chegada_em is None or paciente.chegada_em > fechamento_utc:
                continue

            saida = saidas_por_paciente.get(paciente.id)

            if saida is not None and saida <= fechamento_utc:
                continue

            if em_leito(paciente, fechamento_utc):
                ocupados += 1

        ocupacoes_diarias.append(ocupados / total_leitos * 100)

        if dia == ultimo_dia:
            ocupados_ultimo_dia = ocupados

    media = round(sum(ocupacoes_diarias) / len(ocupacoes_diarias), 1)

    return media, ocupados_ultimo_dia


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

    # Saídas registradas no período (Movimentacao + Paciente.saida_em)
    todas_saidas = mapa_saidas(db)

    saidas_no_mes = {
        paciente_id: data_saida
        for paciente_id, data_saida in todas_saidas.items()
        if data_saida is not None and inicio <= data_saida < fim
    }

    saidas = (
        db.query(models.Paciente)
        .filter(models.Paciente.id.in_(list(saidas_no_mes.keys())))
        .all()
        if saidas_no_mes
        else []
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

    # Permanência média das pacientes que saíram no período
    permanencias = [
        (saidas_no_mes[p.id] - p.chegada_em).total_seconds() / 3600
        for p in saidas
        if p.chegada_em
        and saidas_no_mes[p.id] >= p.chegada_em
    ]

    permanencia_media = (
        round(sum(permanencias) / len(permanencias), 1)
        if permanencias else None
    )

    # Leitos ativos e disponíveis
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

    total_leitos = len(leitos_disponiveis)

    # Ocupação média mensal
    ocupacao_media, ocupados = calcular_ocupacao_media(
        db, mes, total_leitos, todas_saidas
    )

    # Macas no mês selecionado (histórico de movimentações, e não a
    # situação de agora). Mês futuro: sem dados.
    total_macas = 0
    espera_media = None

    if inicio <= agora:
        ids_macas = {
            linha[0]
            for linha in (
                db.query(models.Localizacao.id)
                .filter(models.Localizacao.tipo == "maca")
                .all()
            )
        }

        historico = carregar_historico(db, fim)
        limite = min(fim, agora)

        # Primeira alocação em maca de cada paciente dentro do mês.
        primeiras = {}

        for paciente_id, movimentos in historico.items():
            for indice, (data_hora, destino_id) in enumerate(movimentos):
                if destino_id in ids_macas and inicio <= data_hora < fim:
                    primeiras[paciente_id] = indice
                    break

        total_macas = len(primeiras)

        esperas = []

        if primeiras:
            pacientes_maca = (
                db.query(models.Paciente)
                .filter(models.Paciente.id.in_(list(primeiras.keys())))
                .all()
            )

            for p in pacientes_maca:
                if not p.chegada_tem_hora or p.chegada_em is None:
                    continue

                movimentos = historico[p.id]
                indice = primeiras[p.id]

                # A espera termina quando a paciente sai da maca (próxima
                # movimentação ou saída). Se ainda está nela, vai até
                # agora (ou até o fim do mês, se o mês já terminou).
                encerramentos = [limite]

                if indice + 1 < len(movimentos):
                    encerramentos.append(movimentos[indice + 1][0])

                saida = todas_saidas.get(p.id)
                if saida is not None:
                    encerramentos.append(saida)

                fim_espera = min(encerramentos)

                if fim_espera < p.chegada_em:
                    continue

                esperas.append(
                    (fim_espera - p.chegada_em).total_seconds() / 60
                )

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
        },
        "permanencia": {
            "media_horas": permanencia_media,
            "ocupacao_media": ocupacao_media,
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
        ("atendidas", relatorio["atendimentos"]["atendidas"]),
        ("internadas atualmente", relatorio["atendimentos"]["internadas"]),
        ("altas", relatorio["saidas"]["altas"]),
        ("transferencias", relatorio["saidas"]["transferencias"]),
        ("alojamento_conjunto", relatorio["saidas"]["alojamento"]),
        ("nascimentos", relatorio["nascimentos"]["total"]),
        ("parto_vaginal", relatorio["nascimentos"]["normal"]),
        ("cesareas", relatorio["nascimentos"]["cesarea"]),
        ("natimortos", relatorio["obitos"]["neonatais"]),
        ("permanencia_media_horas", relatorio["permanencia"]["media_horas"]),
        (
            "ocupacao_media_mensal_percentual",
            relatorio["permanencia"]["ocupacao_media"],
        ),
        ("atendidas_em_maca", relatorio["macas"]["atendidas"]),
        ("espera_media_minutos", relatorio["macas"]["espera_media_minutos"]),
    ]

    return linhas


def gerar_csv(relatorio: dict):
    arquivo = io.StringIO()
    escritor = csv.writer(arquivo, delimiter=";")

    escritor.writerow(["métrica", "valor"])

    for metrica, valor in dados_csv(relatorio):
        escritor.writerow([metrica, valor if valor is not None else "Não disponível"])

    return "\ufeff" + arquivo.getvalue()


def _valor_pdf(valor):
    return valor if valor is not None else "—"


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
        [
            "Permanência média (horas)",
            _valor_pdf(relatorio["permanencia"]["media_horas"]),
        ],
        [
            "Ocupação média mensal (%)",
            _valor_pdf(relatorio["permanencia"]["ocupacao_media"]),
        ],
        ["Atendidas em maca", relatorio["macas"]["atendidas"]],
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
            "Os indicadores refletem os registros disponíveis no sistema. "
            "A ocupação média considera a média das ocupações diárias dos "
            "leitos disponíveis.",
            estilos["Italic"],
        ),
    ])

    documento.build(conteudo)

    arquivo.seek(0)
    return arquivo