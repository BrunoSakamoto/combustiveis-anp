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
        valor_venda,
        data_coleta,
        try_cast(replace(valor_venda, ',', '.') as decimal(8, 3))        as preco,
        try_strptime(data_coleta, '%d/%m/%Y')::date                      as data,
        regexp_replace(cnpj, '[^0-9]', '', 'g')                          as cnpj,
        upper(regexp_replace(trim(produto), '\\s+', ' ', 'g'))           as produto
    from bruto.precos_ca
),
validas as (
    select * from t where preco > 0 and data is not null and coalesce(cnpj, '') <> ''
)
select
    arquivo,
    count(*)                                                                    as linhas,
    count(*) filter (where preco is null or preco <= 0)                         as sem_preco_valido,
    count(*) filter (where data is null)                                        as data_invalida,
    count(*) filter (where coalesce(cnpj, '') = '')                             as sem_cnpj,
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
where try_cast(replace(valor_venda, ',', '.') as decimal(8, 3)) is null
   or try_cast(replace(valor_venda, ',', '.') as decimal(8, 3)) <= 0
group by 1 order by 2 desc limit 5
"""

EXEMPLOS_DATA = """
select data_coleta, count(*) as vezes
from bruto.precos_ca
where try_strptime(data_coleta, '%d/%m/%Y') is null
group by 1 order by 2 desc limit 5
"""

FORA_DA_CURVA = """
select uf, municipio, produto, data_coleta, preco_venda,
       round(desvio_media_municipio * 100, 1) as desvio_pct, revenda
from analise.fct_coletas
where abs(desvio_media_municipio) > 0.6
order by abs(desvio_media_municipio) desc
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
        _tabela(con, "Coletas mais de 60% acima ou abaixo da média do município na semana", FORA_DA_CURVA)
