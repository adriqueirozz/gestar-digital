"""Importação da planilha para o banco.

Regras (documento do MVP):
- Os dados de ORIGEM (nome, GPA, IG, diagnóstico, OBS, data de entrada) vêm da planilha.
- A localização é do Gestar: uma reimportação NUNCA move uma paciente que já existe.
- A paciente é reconhecida pelo código do prontuário.
- Erro de digitação não faz a paciente sumir: ela entra na fila e o problema vai para a conferência.
  Só ficam de fora as linhas sem prontuário numérico ou sem nome.
"""
from datetime import timedelta

from sqlalchemy.orm import Session

from app import models
from app.services import planilha

FUSO_LOCAL_EM_HORAS = 3  # Pernambuco é UTC-3; o banco guarda UTC


def para_utc(data_local):
    return data_local + timedelta(hours=FUSO_LOCAL_EM_HORAS)


def importar(db: Session, conteudo: bytes, nome_arquivo: str, usuario_id: int | None = None) -> dict:
    df = planilha.ler_planilha(conteudo, nome_arquivo)
    linhas = planilha.interpretar(df)  # pode levantar ValueError (coluna faltando, formato inválido)

    importacao = models.Importacao(
        origem="excel" if nome_arquivo.lower().endswith((".xlsx", ".xlsm")) else "csv",
        arquivo=nome_arquivo, usuario_id=usuario_id,
    )
    db.add(importacao)
    db.flush()

    leitos = {l.codigo: l for l in db.query(models.Localizacao).filter(models.Localizacao.tipo == "leito")}
    codigos = {l.id: l.codigo for l in leitos.values()}
    ativos = db.query(models.Paciente).filter(models.Paciente.status == "ativa").all()
    ocupados = {p.localizacao_id for p in ativos if p.localizacao_id}
    existentes = {
        p.prontuario: p
        for p in db.query(models.Paciente).filter(models.Paciente.prontuario.in_([l.prontuario for l in linhas]))
    }

    novas = atualizadas = alocadas = na_fila = ignoradas = 0
    linhas_com_problema = set()

    def problema(ln, tipo, valor, detalhe):
        linhas_com_problema.add(ln.linha)
        db.add(models.ImportacaoProblema(importacao_id=importacao.id, linha=ln.linha,
                                         valor=valor, tipo=tipo, detalhe=detalhe))

    vistos = set()  # prontuários já processados neste arquivo

    for ln in linhas:
        for tipo, valor, detalhe in ln.problemas:
            problema(ln, tipo, valor, detalhe)
        if ln.ignorada:
            ignoradas += 1
            continue
        if ln.prontuario in vistos:
            problema(ln, "prontuario_duplicado", ln.prontuario,
                     "Este prontuário já apareceu antes no arquivo. Linha não importada.")
            ignoradas += 1
            continue
        vistos.add(ln.prontuario)

        # leito pedido pela planilha (só vale se existir e estiver utilizável)
        destino = None
        if ln.leito_codigo:
            leito = leitos.get(ln.leito_codigo)
            if leito is None:
                problema(ln, "leito_inexistente", ln.leito_texto, f"O leito {ln.leito_codigo} não existe no COB.")
            elif leito.situacao == "indisponivel":
                problema(ln, "leito_indisponivel", ln.leito_texto, f"O leito {ln.leito_codigo} está indisponível.")
            else:
                destino = leito

        chegada = para_utc(ln.chegada_local) if ln.chegada_local else models.agora()
        campos_origem = dict(
            nome=ln.nome,
            diagnostico=ln.diagnostico or None,
            observacoes_origem=ln.obs or None,
            leito_origem=ln.leito_texto or None,
            linha_origem=ln.linha,
            dados_origem=ln.bruto,
            importacao_id=importacao.id,
        )
        if ln.gpa:
            campos_origem.update(gestas=ln.gpa[0], partos=ln.gpa[1], abortos=ln.gpa[2])
        if ln.ig:
            campos_origem.update(ig_semanas=ln.ig[0], ig_dias=ln.ig[1])
        if ln.chegada_local:
            campos_origem.update(chegada_em=chegada, chegada_tem_hora=ln.chegada_tem_hora)

        paciente = existentes.get(ln.prontuario)
        if paciente:
            # reimportação: atualiza só dados de origem; localização e estado continuam do Gestar
            for campo, valor in campos_origem.items():
                setattr(paciente, campo, valor)
            atualizadas += 1
            if destino and paciente.localizacao_id != destino.id:
                atual = codigos.get(paciente.localizacao_id, "fila / outro local")
                problema(ln, "divergencia", ln.leito_texto,
                         f"A planilha indica {destino.codigo}, mas no Gestar a paciente está em {atual}. Nada foi alterado.")
            continue

        # paciente nova
        if destino and destino.id in ocupados:
            problema(ln, "leito_ocupado", ln.leito_texto,
                     f"O leito {destino.codigo} já está ocupado por outra paciente. Ela foi para a fila.")
            destino = None

        paciente = models.Paciente(
            prontuario=ln.prontuario, perfil=ln.perfil,
            chegada_em=chegada, chegada_tem_hora=ln.chegada_tem_hora,
            localizacao_id=destino.id if destino else None,
        )
        for campo, valor in campos_origem.items():
            setattr(paciente, campo, valor)
        db.add(paciente)
        db.flush()
        novas += 1

        if destino:
            ocupados.add(destino.id)
            alocadas += 1
            db.add(models.Movimentacao(paciente_id=paciente.id, destino_id=destino.id, motivo="alocacao",
                                       observacao="Carga inicial da planilha", usuario_id=usuario_id))
        else:
            na_fila += 1

    importacao.linhas_lidas = len(linhas)
    importacao.linhas_com_problema = len(linhas_com_problema)
    db.commit()

    return {"importacao_id": importacao.id, "arquivo": nome_arquivo, "linhas_lidas": len(linhas),
            "novas": novas, "atualizadas": atualizadas, "alocadas": alocadas, "na_fila": na_fila,
            "ignoradas": ignoradas, "linhas_com_problema": len(linhas_com_problema),
            "problemas": listar_problemas(db, importacao.id)}


def listar_problemas(db: Session, importacao_id: int) -> list[dict]:
    itens = (db.query(models.ImportacaoProblema)
             .filter(models.ImportacaoProblema.importacao_id == importacao_id)
             .order_by(models.ImportacaoProblema.linha, models.ImportacaoProblema.id).all())
    return [{"linha": i.linha, "valor": i.valor, "tipo": i.tipo, "detalhe": i.detalhe} for i in itens]