"""Leitura e normalização da planilha de pacientes do COB.

Este módulo NÃO acessa o banco: só lê o arquivo e interpreta cada linha.
Assim dá para testar rápido e trocar a fonte (CSV, Excel, Microsoft Graph) depois.

Colunas da planilha oficial, nesta ordem:
leito, código do prontuário, data de entrada no COB, nome completo,
GPA (formato G1P2A3), IG (semanas), diagnóstico (texto livre), OBS (texto livre).
"""
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO, StringIO

import pandas as pd

# Nome interno -> títulos de coluna aceitos (já sem acento, minúsculos, só letras e números)
ALIASES = {
    "leito": ["leito"],
    "prontuario": ["prontuario", "codigo do prontuario", "codigo prontuario", "cod prontuario",
                   "numero do prontuario", "n prontuario"],
    "data_entrada": ["data de entrada no cob", "data de entrada", "data entrada", "entrada", "data"],
    "nome": ["nome completo", "nome", "paciente"],
    "gpa": ["gpa", "g p a"],
    "ig": ["ig", "idade gestacional", "ig semanas"],
    "diagnostico": ["diagnostico", "dx", "hd"],
    "obs": ["obs", "observacao", "observacoes"],
}
OBRIGATORIAS = ["leito", "prontuario", "data_entrada", "nome", "gpa", "ig", "diagnostico"]  # OBS é opcional


def sem_acentos(texto) -> str:
    t = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in t if not unicodedata.combining(c))


def chave(texto) -> str:
    """'Código do Prontuário' -> 'codigo do prontuario'."""
    t = re.sub(r"[^a-z0-9]+", " ", sem_acentos(texto).lower())
    return t.strip()


def limpar(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and pd.isna(valor):
        return ""
    texto = str(valor).strip()
    return "" if texto.lower() in ("nan", "none", "nat") else texto


# ---------------------------------------------------------------- leitura do arquivo
def ler_planilha(conteudo: bytes, nome_arquivo: str) -> pd.DataFrame:
    """Lê CSV ou Excel (.xlsx). Tudo é lido como texto para não perder zeros do prontuário."""
    nome = (nome_arquivo or "").lower()
    if nome.endswith((".xlsx", ".xlsm")):
        df = pd.read_excel(BytesIO(conteudo), dtype=str)
    elif nome.endswith((".csv", ".txt")):
        texto = None
        for codificacao in ("utf-8-sig", "cp1252"):  # Excel em português costuma salvar em cp1252
            try:
                texto = conteudo.decode(codificacao)
                break
            except UnicodeDecodeError:
                continue
        if texto is None:
            raise ValueError("Não foi possível ler o arquivo (codificação desconhecida).")
        linhas = texto.splitlines()
        if not linhas:
            raise ValueError("O arquivo está vazio.")
        separador = max([";", ",", "\t"], key=linhas[0].count)
        df = pd.read_csv(StringIO(texto), sep=separador, dtype=str)
    else:
        raise ValueError("Formato não suportado. Envie um arquivo .csv ou .xlsx.")
    return df.dropna(how="all")


def mapear_colunas(df: pd.DataFrame) -> dict:
    """Descobre qual coluna do arquivo é qual campo (aceita variações de título)."""
    achadas = {}
    for coluna in df.columns:
        k = chave(coluna)
        for interno, variacoes in ALIASES.items():
            if k in variacoes and interno not in achadas:
                achadas[interno] = coluna
    faltando = [c for c in OBRIGATORIAS if c not in achadas]
    if faltando:
        raise ValueError(
            "Colunas não encontradas: " + ", ".join(faltando)
            + ". Colunas recebidas: " + ", ".join(str(c) for c in df.columns)
        )
    return achadas


# ---------------------------------------------------------------- normalização de campos
RE_LEITO = re.compile(r"^(?:ENF(?:ERMARIA)?\.?\s*|E\s*)?0*(\d{1,2})\s*[-–/.\s]*\s*(?:LEITO\s*)?([A-Z])$")


def normalizar_leito(texto: str) -> str | None:
    """'Enf 3 - Leito A', 'E3A', '3A' -> 'E3A'. Devolve None se não reconhecer o formato."""
    m = RE_LEITO.match(sem_acentos(texto).upper().strip())
    if not m:
        return None
    return f"E{int(m.group(1))}{m.group(2)}"


RE_GPA = re.compile(r"^G\s*(\d+)\s*P\s*(\d+)\s*A\s*(\d+)$", re.IGNORECASE)


def parse_gpa(texto: str) -> tuple[int, int, int] | None:
    """'G1P2A3' -> (1, 2, 3)."""
    m = RE_GPA.match(texto.strip())
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


RE_IG_SEMANAS = re.compile(r"^(\d{1,2})\s*(?:s|sem\w*)?$", re.IGNORECASE)
RE_IG_COM_DIAS = re.compile(r"^(\d{1,2})\s*(?:s|sem\w*)?\s*[+\s]?\s*(\d)\s*d\w*$", re.IGNORECASE)
RE_IG_MAIS = re.compile(r"^(\d{1,2})\s*\+\s*(\d)$")


def parse_ig(texto: str) -> tuple[int, int | None] | None:
    """'39', '39s', '39 semanas' -> (39, None); '39s2d' ou '39+2' -> (39, 2)."""
    t = texto.strip()
    semanas = dias = None
    if m := RE_IG_SEMANAS.match(t):
        semanas = int(m.group(1))
    elif m := (RE_IG_COM_DIAS.match(t) or RE_IG_MAIS.match(t)):
        semanas, dias = int(m.group(1)), int(m.group(2))
    if semanas is None or not (1 <= semanas <= 45) or (dias is not None and dias > 6):
        return None
    return semanas, dias


def parse_data(texto: str) -> tuple[datetime | None, bool]:
    """Devolve (data/hora, tem_hora). A planilha pode trazer só a data; nesse caso tem_hora = False."""
    if not texto:
        return None, False
    ts = pd.to_datetime(texto, dayfirst=True, errors="coerce")
    if pd.isna(ts):
        return None, False
    tem_hora = ":" in texto and bool(ts.hour or ts.minute)
    return ts.to_pydatetime(), tem_hora


def inferir_perfil(diagnostico: str, obs: str) -> str:
    """Sugestão inicial a partir do texto livre. A enfermagem confirma/corrige no sistema."""
    t = chave(f"{diagnostico} {obs}")
    if any(p in t for p in ("abort", "curet", "amiu")):
        return "abortamento"
    if any(p in t for p in ("puerper", "pos parto", "pos cesar", "pos pn")):
        return "puerpera"
    return "gestante"


# ---------------------------------------------------------------- interpretação das linhas
@dataclass
class LinhaPlanilha:
    linha: int  # número da linha na planilha (o cabeçalho é a linha 1)
    bruto: dict
    prontuario: str = ""
    nome: str = ""
    leito_texto: str = ""
    leito_codigo: str | None = None
    gpa: tuple | None = None
    ig: tuple | None = None
    chegada_local: datetime | None = None
    chegada_tem_hora: bool = False
    diagnostico: str = ""
    obs: str = ""
    perfil: str = "gestante"
    ignorada: bool = False  # sem prontuário válido ou sem nome: não dá para importar
    problemas: list = field(default_factory=list)  # (tipo, valor, detalhe)


def interpretar(df: pd.DataFrame) -> list[LinhaPlanilha]:
    col = mapear_colunas(df)
    pegar = lambda row, campo: limpar(row[col[campo]]) if campo in col else ""
    resultado = []

    for indice, row in df.iterrows():
        ln = LinhaPlanilha(linha=int(indice) + 2, bruto={str(c): limpar(row[c]) for c in df.columns})

        # prontuário: é a chave que liga a linha ao paciente
        bruto = pegar(row, "prontuario")
        ln.prontuario = bruto[:-2] if bruto.endswith(".0") else bruto
        if not re.fullmatch(r"\d+", ln.prontuario):
            ln.ignorada = True
            ln.problemas.append(("prontuario_invalido", bruto, "O código do prontuário deve ser numérico. Linha não importada."))
        ln.nome = pegar(row, "nome")
        if not ln.nome:
            ln.ignorada = True
            ln.problemas.append(("campo_vazio", "", "Nome vazio. Linha não importada."))
        if ln.ignorada:
            resultado.append(ln)
            continue

        # leito vazio é normal: a paciente vai para a fila de alocação
        ln.leito_texto = pegar(row, "leito")
        if ln.leito_texto:
            ln.leito_codigo = normalizar_leito(ln.leito_texto)
            if ln.leito_codigo is None:
                ln.problemas.append(("leito_nao_reconhecido", ln.leito_texto,
                                     "Formato de leito não reconhecido. Exemplos aceitos: Enf 3 - Leito A, E3A."))

        texto = pegar(row, "gpa")
        if not texto:
            ln.problemas.append(("campo_vazio", "", "GPA vazio."))
        else:
            ln.gpa = parse_gpa(texto)
            if ln.gpa is None:
                ln.problemas.append(("formato_invalido", texto, "GPA deve ter o formato G1P2A3."))

        texto = pegar(row, "ig")
        if not texto:
            ln.problemas.append(("campo_vazio", "", "IG vazia."))
        else:
            ln.ig = parse_ig(texto)
            if ln.ig is None:
                ln.problemas.append(("formato_invalido", texto, "IG deve ser em semanas (ex.: 39)."))

        texto = pegar(row, "data_entrada")
        if not texto:
            ln.problemas.append(("campo_vazio", "", "Data de entrada vazia."))
        else:
            ln.chegada_local, ln.chegada_tem_hora = parse_data(texto)
            if ln.chegada_local is None:
                ln.problemas.append(("formato_invalido", texto, "Data de entrada não reconhecida (use dd/mm/aaaa)."))

        ln.diagnostico = pegar(row, "diagnostico")
        ln.obs = pegar(row, "obs")
        ln.perfil = inferir_perfil(ln.diagnostico, ln.obs)
        resultado.append(ln)

    return resultado