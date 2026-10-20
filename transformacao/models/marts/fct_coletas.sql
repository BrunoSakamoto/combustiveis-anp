-- Fato principal: cada coleta, com o desvio do preço em relação à média do município
-- naquela semana. É a base para comparar bandeiras e achar postos fora da curva.

with coletas as (
    select * from {{ ref('stg_precos') }}
)

select
    regiao,
    uf,
    municipio,
    cnpj,
    revenda,
    bandeira,
    produto,
    unidade,
    data_coleta,
    semana,
    preco_venda,
    round(
        preco_venda / avg(preco_venda) over (partition by municipio, uf, produto, semana) - 1,
        4
    ) as desvio_media_municipio,
    arquivo_origem
from coletas
