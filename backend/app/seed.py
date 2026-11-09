"""Popula o banco com dados SIMULADOS para desenvolvimento e demonstração.

Uso (dentro de backend/):
    python -m app.seed                    catálogo + pacientes de demonstração
    python -m app.seed --sem-pacientes    só o catálogo (leitos, salas, macas): ideal para demonstrar a importação
    python -m app.seed --recriar          apaga TUDO e popula de novo (pode ser combinado com a opção anterior)
"""
import sys
from datetime import timedelta

from app import models
from app.database import Base, SessionLocal, engine

# ---- catálogo do COB (ajuste aqui se o hospital confirmar números diferentes) ----
NUM_ENFERMARIAS = 9
LETRAS_LEITO = "ABC"      # leitos por enfermaria: a planilha traz A, B e C; o documento da visita dizia 2. Confirmar.
INDISPONIVEIS = {"E9B"}   # leitos fora de uso
EM_LIMPEZA = {"E3B"}      # leitos em limpeza no momento
NUM_SALAS_PARTO = 3       # a confirmar com o hospital
NUM_SALAS_CIRURGIA = 2

# ---- pacientes de demonstração (todos fictícios) ----
# local: código do leito/maca, ou None para ficar na fila de alocação; espera = minutos desde a chegada
PACIENTES = [
    dict(nome="Joana Maria Lima", gpa=(2, 1, 0), ig=(39, 2), dx="Trabalho de parto ativo", perfil="gestante",
         local="E1A", espera=215, parindo=True, alergia="Dipirona", reserva=True),
    dict(nome="Fernanda Lúcia Alves", gpa=(3, 2, 0), ig=(38, 5), dx="DHEG", perfil="gestante",
         local="E1B", espera=520, comorbidade=True, reserva=True),
    dict(nome="Luciana Pereira Costa", gpa=(2, 2, 0), ig=(39, 0), dx="Puérpera pós parto normal", perfil="puerpera",
         local="E2A", espera=1700, parto_h=28, parto_tipo="normal"),
    dict(nome="Aline Souza Barros", gpa=(1, 1, 0), ig=(40, 1), dx="Puérpera pós cesárea", perfil="puerpera",
         local="E2B", espera=2900, parto_h=46, parto_tipo="cesarea", atb=True),
    dict(nome="Patrícia Gomes Melo", gpa=(4, 1, 2), ig=(9, 0), dx="Abortamento retido, aguarda curetagem",
         perfil="abortamento", local="E3A", espera=260, reserva=True),
    dict(nome="Gabriela Nunes Freitas", gpa=(2, 0, 1), ig=(40, 3), dx="Indução programada", perfil="gestante",
         local="M1", espera=130),
    dict(nome="Mônica Dias Silveira", gpa=(2, 1, 0), ig=(38, 0), dx="Trabalho de parto, bolsa rota", perfil="gestante",
         local=None, espera=35, parindo=True, bolsa_h=21, alergia="Penicilina"),
    dict(nome="Carolina Helena Ferraz", gpa=(1, 0, 0), ig=(34, 6), dx="Diabetes gestacional descompensado",
         perfil="gestante", local=None, espera=65, comorbidade=True),
]


def criar_catalogo(db) -> dict:
    locais = {}

    def novo(codigo, tipo, nome, **extra):
        locais[codigo] = models.Localizacao(codigo=codigo, tipo=tipo, nome=nome, **extra)

    for n in range(1, NUM_ENFERMARIAS + 1):
        for letra in LETRAS_LEITO:
            codigo = f"E{n}{letra}"
            situacao = "indisponivel" if codigo in INDISPONIVEIS else "limpeza" if codigo in EM_LIMPEZA else "normal"
            novo(codigo, "leito", f"Enf. {n} · Leito {letra}", enfermaria=n, situacao=situacao)

    for i in range(1, NUM_SALAS_PARTO + 1):
        novo(f"PN{i}", "sala_parto", f"Sala de parto {i}")
    for i in range(1, NUM_SALAS_CIRURGIA + 1):
        novo(f"CC{i}", "centro_cirurgico", f"Centro cirúrgico {i}")
    for codigo, nome in (("USG", "Ultrassonografia"), ("PSI", "Psicologia"), ("SS", "Serviço social")):
        novo(codigo, "apoio", nome)
    novo("M1", "maca", "Maca 1", descricao="Corredor próx. à enf. 3")

    db.add_all(locais.values())
    db.flush()  # gera os ids
    return locais


def criar_pacientes(db, locais: dict) -> None:
    agora = models.agora()
    for i, d in enumerate(PACIENTES):
        local = locais[d["local"]] if d["local"] else None
        paciente = models.Paciente(
            prontuario=str(200001 + i),  # números fictícios, fora da faixa do CSV de exemplo (104xxx)
            nome=d["nome"],
            gestas=d["gpa"][0], partos=d["gpa"][1], abortos=d["gpa"][2],
            ig_semanas=d["ig"][0], ig_dias=d["ig"][1],
            diagnostico=d["dx"], perfil=d["perfil"],
            parindo=d.get("parindo", False), comorbidade=d.get("comorbidade", False),
            alergia=d.get("alergia"), reserva_sanguinea=d.get("reserva", False), atb=d.get("atb", False),
            bolsa_rota_em=agora - timedelta(hours=d["bolsa_h"]) if d.get("bolsa_h") else None,
            chegada_em=agora - timedelta(minutes=d["espera"]), chegada_tem_hora=True,
            localizacao_id=local.id if local else None,
        )
        db.add(paciente)
        db.flush()

        if local:
            db.add(models.Movimentacao(paciente_id=paciente.id, destino_id=local.id, motivo="alocacao",
                                       observacao="Seed de demonstração"))
        if d.get("parto_h") is not None:
            db.add(models.Parto(paciente_id=paciente.id, data_hora=agora - timedelta(hours=d["parto_h"]),
                                tipo=d["parto_tipo"], nascimento="vivo"))


def seed(com_pacientes: bool = True, recriar: bool = False) -> None:
    if recriar:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        if db.query(models.Localizacao).count():
            print("O banco já está populado. Use --recriar para apagar tudo e começar de novo.")
            return

        locais = criar_catalogo(db)
        db.add(models.Configuracao(chave="limite_lotacao", valor="85"))
        if com_pacientes:
            criar_pacientes(db, locais)
        db.commit()

        leitos = [c for c, l in locais.items() if l.tipo == "leito"]
        disponiveis = [c for c in leitos if c not in INDISPONIVEIS]
        print(f"Seed concluído: {len(leitos)} leitos ({len(disponiveis)} disponíveis), "
              f"{NUM_SALAS_PARTO} salas de parto, {NUM_SALAS_CIRURGIA} de cirurgia, 1 maca, "
              f"{len(PACIENTES) if com_pacientes else 0} pacientes.")
    finally:
        db.close()


if __name__ == "__main__":
    seed(com_pacientes="--sem-pacientes" not in sys.argv, recriar="--recriar" in sys.argv)