"""Relatório de qualidade: por que linhas foram descartadas e quais coletas fogem da curva.

    python -m combustiveis qualidade

Complementa os testes do dbt: os testes dizem *que* algo saiu do esperado, este relatório
mostra *o quê*, com exemplos, para decidir se é problema da origem ou do pipeline.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from . import config

MOTIVOS = """
with t as (
    select
        _arquivo                                                         as arquivo,
        coalesce(uf, municipio, cnpj, produto, data_coleta, valor_venda) is null as vazia,
        valor_venda,
        data_coleta,
        try_cast(replace(valor_venda, ',', '.') as decimal(8, 3))        as preco,
        try_strptime(data_coleta, '%d/%m/%Y')::date                      as data,
        regexp_replace(cnpj, '[^0-9]', '', 'g')                          as cnpj,
        upper(regexp_replace(trim(produto), '\\s+', ' ', 'g'))           as produto
    from bruto.precos_ca
),
validas as (
    select * from t where not vazia and preco > 0 and data is not null and coalesce(cnpj, '') <> ''
)
select
    arquivo,
    count(*)                                                                    as linhas,
    count(*) filter (where vazia)                                               as vazias,
    count(*) filter (where not vazia and (preco is null or preco <= 0))         as sem_preco_valido,
    count(*) filter (where not vazia and data is null)                          as data_invalida,
    count(*) filter (where not vazia and coalesce(cnpj, '') = '')               as sem_cnpj,
    (select count(*) from validas v where v.arquivo = t.arquivo)
      - (select count(distinct (cnpj, produto, data)) from validas v where v.arquivo = t.arquivo)
                                                                                as duplicadas
from t
group by arquivo
order by arquivo
"""

EXEMPLOS_PRECO = """
select valor_venda, count(*) as vezes
from bruto.precos_ca
where coalesce(uf, municipio, cnpj, produto, data_coleta, valor_venda) is not null
  and (try_cast(replace(valor_venda, ',', '.') as decimal(8, 3)) is null
       or try_cast(replace(valor_venda, ',', '.') as decimal(8, 3)) <= 0)
group by 1 order by 2 desc limit 5
"""

EXEMPLOS_DATA = """
select data_coleta, count(*) as vezes
from bruto.precos_ca
where coalesce(uf, municipio, cnpj, produto, data_coleta, valor_venda) is not null
  and try_strptime(data_coleta, '%d/%m/%Y') is null
group by 1 order by 2 desc limit 5
"""

FORA_DA_CURVA = """
select uf, municipio, produto, data_coleta, preco_venda,
       round(desvio_mediana_uf * 100, 1) as desvio_mediana_uf_pct, revenda
from analise.fct_coletas
where fora_da_curva
order by abs(desvio_mediana_uf) desc
limit 20
"""


def _tabela(con: duckdb.DuckDBPyConnection, titulo: str, sql: str) -> None:
    print(f"\n{titulo}")
    try:
        con.sql(sql).show(max_width=160)
    except duckdb.CatalogException:
        print("  (tabela ainda não existe; rode o pipeline antes)")


def relatorio(banco: Path = config.CAMINHO_BANCO) -> None:
    if not banco.exists():
        raise FileNotFoundError(f"Banco não encontrado: {banco}")
    with duckdb.connect(str(banco), read_only=True) as con:
        _tabela(con, "Linhas descartadas no staging, por motivo e arquivo", MOTIVOS)
        _tabela(con, "Exemplos de preço que não virou número", EXEMPLOS_PRECO)
        _tabela(con, "Exemplos de data que não foi lida", EXEMPLOS_DATA)
        _tabela(con, "Coletas fora da curva: mais de 60% longe da mediana do estado (fora das médias)",
               FORA_DA_CURVA)
