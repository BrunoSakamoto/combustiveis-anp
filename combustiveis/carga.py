"""Carga dos CSVs da ANP na camada bruta do DuckDB (`bruto.precos_ca`).

A camada bruta guarda tudo como texto, exatamente como veio, mais duas colunas de linhagem
(`_arquivo`, `_carregado_em`). Tipos e limpeza ficam no dbt. Recarregar um arquivo apaga as
linhas dele antes de inserir, então rodar a carga duas vezes não duplica nada.

Os arquivos variam entre anos (acentos no cabeçalho, encoding UTF-8 ou Latin-1, BOM), por isso
o cabeçalho é normalizado e mapeado para nomes canônicos.
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from pathlib import Path

import duckdb

from . import config

log = logging.getLogger(__name__)

# Nome canônico -> variações conhecidas (já normalizadas por `_normalizar`).
COLUNAS = {
    "regiao": ["regiao_sigla", "regiao"],
    "uf": ["estado_sigla", "estado", "uf"],
    "municipio": ["municipio"],
    "revenda": ["revenda"],
    "cnpj": ["cnpj_da_revenda", "cnpj"],
    "rua": ["nome_da_rua", "rua"],
    "numero": ["numero_rua", "numero"],
    "complemento": ["complemento"],
    "bairro": ["bairro"],
    "cep": ["cep"],
    "produto": ["produto"],
    "data_coleta": ["data_da_coleta", "data_coleta"],
    "valor_venda": ["valor_de_venda", "valor_venda"],
    "valor_compra": ["valor_de_compra", "valor_compra"],
    "unidade": ["unidade_de_medida", "unidade"],
    "bandeira": ["bandeira"],
}
OBRIGATORIAS = {"uf", "municipio", "cnpj", "produto", "data_coleta", "valor_venda"}

DDL = f"""
create schema if not exists bruto;
create table if not exists bruto.precos_ca (
    {", ".join(f"{c} varchar" for c in COLUNAS)},
    _arquivo varchar not null,
    _hash varchar not null,
    _carregado_em timestamp not null default current_timestamp
);
"""


def _normalizar(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_")


def _detectar_formato(caminho: Path) -> tuple[str, str, list[str]]:
    """Devolve (encoding, separador, cabeçalho) olhando só o início do arquivo."""
    amostra = caminho.read_bytes()[:65536]
    try:
        texto, encoding = amostra.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        texto, encoding = amostra.decode("latin-1"), "latin-1"
    primeira = texto.lstrip("﻿").splitlines()[0]
    separador = max([";", ",", "\t"], key=primeira.count)
    cabecalho = [c.strip().strip('"') for c in primeira.split(separador)]
    return encoding, separador, cabecalho


def mapear_cabecalho(cabecalho: list[str]) -> dict[str, str]:
    """Nome original no arquivo -> nome canônico. Falha se faltar coluna essencial."""
    reverso = {variacao: canonico for canonico, vs in COLUNAS.items() for variacao in vs}
    mapa = {}
    for original in cabecalho:
        canonico = reverso.get(_normalizar(original))
        if canonico and canonico not in mapa.values():
            mapa[original] = canonico
    faltando = OBRIGATORIAS - set(mapa.values())
    if faltando:
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(faltando)}. Cabeçalho: {cabecalho}")
    return mapa


def _hash_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()[:16]


def carregar_arquivo(con: duckdb.DuckDBPyConnection, caminho: Path) -> int:
    """Carrega um CSV; pula se o mesmo conteúdo já está no banco. Devolve linhas inseridas."""
    hash_atual = _hash_arquivo(caminho)
    ja = con.execute(
        "select any_value(_hash) from bruto.precos_ca where _arquivo = ?", [caminho.name]
    ).fetchone()[0]
    if ja == hash_atual:
        log.info("%s sem mudanças, pulando", caminho.name)
        return 0

    encoding, sep, cabecalho = _detectar_formato(caminho)
    mapa = mapear_cabecalho(cabecalho)
    selecao = ", ".join(
        f'nullif(trim("{orig}"), \'\') as {canon}' for orig, canon in mapa.items()
    )
    faltantes = [c for c in COLUNAS if c not in mapa.values()]
    nulos = "".join(f", null::varchar as {c}" for c in faltantes)

    con.execute("begin transaction")
    try:
        con.execute("delete from bruto.precos_ca where _arquivo = ?", [caminho.name])
        con.execute(
            f"""
            insert into bruto.precos_ca by name
            select {selecao}{nulos}, ? as _arquivo, ? as _hash
            from read_csv(?, delim = ?, header = true, all_varchar = true,
                          encoding = ?, quote = '"', ignore_errors = false)
            """,
            [caminho.name, hash_atual, str(caminho), sep, encoding],
        )
        linhas = con.execute(
            "select count(*) from bruto.precos_ca where _arquivo = ?", [caminho.name]
        ).fetchone()[0]
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise
    log.info("%s: %d linhas (%s, separador %r)", caminho.name, linhas, encoding, sep)
    return linhas


def carregar(
    arquivos: list[Path] | None = None,
    banco: Path = config.CAMINHO_BANCO,
    dir_bruto: Path = config.DIR_BRUTO,
) -> int:
    arquivos = arquivos if arquivos is not None else sorted(dir_bruto.glob("ca-*.csv"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum CSV em {dir_bruto}. Rode a ingestão antes.")
    banco.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(banco)) as con:
        con.execute(DDL)
        return sum(carregar_arquivo(con, a) for a in arquivos)
