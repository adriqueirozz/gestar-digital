from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.database import get_db

router = APIRouter(prefix="/painel", tags=["painel"])

LIMITE_PADRAO = 85  # % de lotação que dispara o alerta (configurável na tabela de configurações)


def _horas(inicio, agora):
    return (agora - inicio).total_seconds() / 3600


def _tags(p, agora) -> list[dict]:
    """Sinalizações curtas da paciente (apoio à decisão; a equipe é quem decide)."""
    tags = []
    if p.parindo:
        tags.append({"txt": "Parindo", "tom": "alerta"})
    if p.comorbidade:
        tags.append({"txt": "Comorbidade", "tom": "aviso"})
    if p.bolsa_rota_em:
        h = int(_horas(p.bolsa_rota_em, agora))
        tags.append({"txt": f"Bolsa rota {h}h", "tom": "alerta" if h >= 18 else "aviso"})
    if p.parto:
        h = int(_horas(p.parto.data_hora, agora))
        tags.append({"txt": f"Pós-parto {h}h", "tom": "alerta" if h >= 42 else "aviso" if h >= 24 else "neutro"})
    if p.atb:
        tags.append({"txt": "ATB", "tom": "info"})
    if p.reserva_sanguinea:
        tags.append({"txt": "Reserva sangue", "tom": "info"})
    if p.tarh:
        tags.append({"txt": "TARH", "tom": "info"})
    if p.alergia:
        tags.append({"txt": f"Alergia: {p.alergia}", "tom": "alerta"})
    return tags


def _prioridade(p, agora) -> tuple[int, str]:
    """Pontuação simples e visível: tempo de espera, bolsa rota, comorbidade, parindo e abortamento."""
    pontos = 0
    if p.parindo:
        pontos += 4
    if p.bolsa_rota_em:
        pontos += 3
    if p.comorbidade:
        pontos += 3
    if p.perfil == "abortamento":
        pontos += 2
    if p.chegada_tem_hora:
        pontos += min(int(_horas(p.chegada_em, agora)), 3)  # +1 por hora de espera, no máximo 3
    nivel = "Alta" if pontos >= 8 else "Média" if pontos >= 4 else "Normal"
    return pontos, nivel


def _resumo(p, agora) -> dict:
    return {"id": p.id, "nome": p.nome, "perfil": p.perfil, "tags": _tags(p, agora)}


@router.get("")
def painel(db: Session = Depends(get_db)):
    agora = models.agora()
    locais = db.query(models.Localizacao).filter(models.Localizacao.ativa.is_(True)).all()
    ativos = db.query(models.Paciente).filter(models.Paciente.status == "ativa").all()
    por_local = {p.localizacao_id: p for p in ativos if p.localizacao_id}
    por_id = {l.id: l for l in locais}

    def situacao(l):
        if l.situacao != "normal":
            return l.situacao
        return "ocupado" if l.id in por_local else "livre"

    # ---- enfermarias
    leitos = sorted((x for x in locais if x.tipo == "leito"), key=lambda x: x.codigo)
    enfermarias = {}
    for l in leitos:
        p = por_local.get(l.id)
        enfermarias.setdefault(l.enfermaria, []).append({
            "codigo": l.codigo,
            "letra": l.codigo[-1],
            "situacao": situacao(l),
            "paciente": _resumo(p, agora) if p else None,
        })

    total = sum(1 for l in leitos if l.situacao != "indisponivel")
    ocupados = sum(1 for l in leitos if situacao(l) == "ocupado")
    indisponiveis = sum(1 for l in leitos if l.situacao == "indisponivel")
    percentual = round(ocupados / total * 100) if total else 0

    config = db.query(models.Configuracao).filter_by(chave="limite_lotacao").first()
    limite = int(config.valor) if config and str(config.valor).isdigit() else LIMITE_PADRAO

    # ---- salas e apoio
    def sala(l):
        p = por_local.get(l.id)
        return {"codigo": l.codigo, "nome": l.nome, "paciente": _resumo(p, agora) if p else None}

    salas_parto = [sala(l) for l in sorted(locais, key=lambda x: x.codigo) if l.tipo == "sala_parto"]
    salas_cirurgia = [sala(l) for l in sorted(locais, key=lambda x: x.codigo) if l.tipo == "centro_cirurgico"]
    apoio = [sala(l) for l in sorted(locais, key=lambda x: x.codigo) if l.tipo == "apoio"]

    # ---- macas e fila (quem espera por leito, ordenado por prioridade)
    macas, fila = [], []
    for p in ativos:
        if p.localizacao_id is not None and por_id.get(p.localizacao_id) is not None \
                and por_id[p.localizacao_id].tipo != "maca":
            continue  # está em leito, sala ou apoio
        maca = por_id.get(p.localizacao_id) if p.localizacao_id else None
        pontos, nivel = _prioridade(p, agora)
        gpa = f"G{p.gestas}P{p.partos}A{p.abortos}" if p.gestas is not None and p.partos is not None and p.abortos is not None else "GPA —"
        ig = f"{p.ig_semanas}s" + (f"{p.ig_dias}d" if p.ig_dias is not None else "") if p.ig_semanas is not None else "—"
        espera = int(_horas(p.chegada_em, agora) * 60) if p.chegada_tem_hora else None
        fila.append({
            **_resumo(p, agora), "gpa": gpa, "ig": ig, "diagnostico": p.diagnostico or "",
            "prioridade": nivel, "pontos": pontos, "espera_min": espera,
            "onde": f"Em maca · {maca.descricao or maca.nome}" if maca else "Recém-chegada · sem local",
        })
        if maca:
            macas.append({"nome": p.nome, "local": maca.descricao or maca.nome, "espera_min": espera})
    fila.sort(key=lambda x: (-x["pontos"], -(x["espera_min"] or 0)))

    # ---- indicadores
    posparto = [p for p in ativos if p.parto]
    pos24 = sum(1 for p in posparto if _horas(p.parto.data_hora, agora) >= 24)
    pos42 = sum(1 for p in posparto if _horas(p.parto.data_hora, agora) >= 42)

    return {
        "ocupacao": {"ocupados": ocupados, "total": total, "percentual": percentual,
                     "indisponiveis": indisponiveis, "limite": limite, "alerta": percentual >= limite},
        "sem_leito": len(macas),
        "aguardando": sum(1 for f in fila if f["onde"].startswith("Recém")),
        "salas": {"parto_em_uso": sum(1 for s in salas_parto if s["paciente"]), "parto_total": len(salas_parto),
                  "cirurgia_em_uso": sum(1 for s in salas_cirurgia if s["paciente"]), "cirurgia_total": len(salas_cirurgia)},
        "pos_parto": {"acima_24h": pos24, "perto_48h": pos42},
        "enfermarias": [{"numero": n, "leitos": ls} for n, ls in sorted(enfermarias.items())],
        "salas_parto": salas_parto,
        "salas_cirurgia": salas_cirurgia,
        "apoio": apoio,
        "macas": macas,
        "fila": fila,
    }