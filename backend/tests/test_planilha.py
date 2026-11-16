from pathlib import Path

import pytest

from app.services import planilha

CSV = Path(__file__).resolve().parents[2] / "data" / "sample" / "pacientes_teste.csv"


@pytest.mark.parametrize("texto, esperado", [
    ("Enf 3 - Leito A", "E3A"),
    ("Enf. 3 Leito A", "E3A"),
    ("ENFERMARIA 1 - LEITO B", "E1B"),
    ("E3A", "E3A"),
    ("3A", "E3A"),
    ("1-C", "E1C"),
    ("Enf 03 - B", "E3B"),
    ("Enf 12 - Leito A", "E12A"),   # formato válido; o catálogo do banco decide se existe
    ("Leito A", None),
    ("3", None),
    ("sala de espera", None),
])
def test_normalizar_leito(texto, esperado):
    assert planilha.normalizar_leito(texto) == esperado


@pytest.mark.parametrize("texto, esperado", [
    ("G1P2A3", (1, 2, 3)),
    ("g2p1a0", (2, 1, 0)),
    ("G 2 P 1 A 0", (2, 1, 0)),
    ("G5P4", None),
    ("", None),
    ("abc", None),
])
def test_parse_gpa(texto, esperado):
    assert planilha.parse_gpa(texto) == esperado


@pytest.mark.parametrize("texto, esperado", [
    ("39", (39, None)),
    ("39s", (39, None)),
    ("36 semanas", (36, None)),
    ("39s2d", (39, 2)),
    ("39+2", (39, 2)),
    ("9", (9, None)),
    ("0", None),
    ("60", None),
    ("39s9d", None),
    ("quarenta", None),
])
def test_parse_ig(texto, esperado):
    assert planilha.parse_ig(texto) == esperado


def test_parse_data():
    data, tem_hora = planilha.parse_data("08/11/2026")
    assert (data.day, data.month, data.year) == (8, 11, 2026) and tem_hora is False
    data, tem_hora = planilha.parse_data("08/11/2026 14:32")
    assert (data.hour, data.minute) == (14, 32) and tem_hora is True
    assert planilha.parse_data("32/13/2026") == (None, False)
    assert planilha.parse_data("") == (None, False)


def test_inferir_perfil():
    assert planilha.inferir_perfil("Abortamento retido", "") == "abortamento"
    assert planilha.inferir_perfil("Puérpera pós cesárea", "") == "puerpera"
    assert planilha.inferir_perfil("DHEG", "") == "gestante"


def test_titulos_de_coluna_com_variacoes():
    import pandas as pd
    df = pd.DataFrame(columns=["Leito", "Código do Prontuário", "Data de entrada no COB", "Nome completo",
                               "GPA", "IG", "Diagnóstico", "OBS."])
    col = planilha.mapear_colunas(df)
    assert col["prontuario"] == "Código do Prontuário"
    assert col["obs"] == "OBS."


def test_coluna_faltando_gera_erro_claro():
    import pandas as pd
    df = pd.DataFrame(columns=["leito", "nome completo"])
    with pytest.raises(ValueError, match="Colunas não encontradas"):
        planilha.mapear_colunas(df)


def test_formato_nao_suportado():
    with pytest.raises(ValueError, match="Formato não suportado"):
        planilha.ler_planilha(b"x", "planilha.pdf")


def test_csv_em_cp1252_com_acentos():
    # Excel em português costuma salvar CSV assim
    conteudo = "leito;prontuario;data;nome;gpa;ig;diagnostico\nE1A;1;08/11/2026;José;G1P0A0;39;Puérpera\n".encode("cp1252")
    df = planilha.ler_planilha(conteudo, "x.csv")
    assert df.iloc[0]["nome"] == "José"


def test_csv_de_exemplo():
    df = planilha.ler_planilha(CSV.read_bytes(), CSV.name)
    linhas = planilha.interpretar(df)
    assert len(linhas) == 13

    por_nome = {ln.nome: ln for ln in linhas}
    joana = por_nome["Joana Maria Lima"]
    assert joana.prontuario == "104521" and joana.leito_codigo == "E1A"
    assert joana.gpa == (2, 1, 0) and joana.ig == (39, None) and joana.problemas == []
    assert joana.chegada_tem_hora is False

    assert por_nome["Renata Ferreira Dias"].leito_codigo == "E3A"          # "E3A" normalizado
    assert por_nome["Renata Ferreira Dias"].perfil == "puerpera"
    assert por_nome["Patrícia Gomes Melo"].perfil == "abortamento"
    assert por_nome["Tatiane Barbosa Rocha"].ig == (36, None)              # "36 semanas"
    assert por_nome["Mônica Dias Silveira"].leito_codigo is None           # sem leito: vai para a fila
    assert por_nome["Mônica Dias Silveira"].problemas == []

    carolina = por_nome["Carolina Helena Ferraz"]
    assert [p[0] for p in carolina.problemas] == ["campo_vazio"]           # GPA vazio
    eliane = por_nome["Eliane Maria Ramos"]
    assert [p[0] for p in eliane.problemas] == ["formato_invalido"]        # G5P4 sem aborto
    viviane = por_nome["Viviane Cardoso Pinto"]
    assert viviane.ignorada and viviane.problemas[0][0] == "prontuario_invalido"

    assert por_nome["Joana Maria Lima"].linha == 2                         # cabeçalho é a linha 1
    com_problema = [ln.linha for ln in linhas if ln.problemas]
    assert len(com_problema) == 3