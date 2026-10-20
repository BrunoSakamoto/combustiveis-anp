-- Fato principal: cada coleta, com o desvio do preço em relação à média do município
-- naquela semana. É a base para comparar bandeiras e achar postos fora da curva.
--
-- Coletas mais de 60% longe da mediana do ESTADO na semana ficam marcadas em `fora_da_curva`.
-- Mediana, porque um valor errado não a desloca; do estado, porque um município pode ter só
-- dois postos na semana, e aí não dá para saber qual dos dois está errado. Diferenças de
-- preço dentro de um estado ficam muito abaixo de 60%. Nos dados reais são casos raros
-- (ex.: etanol registrado com preço de gasolina). Continuam aqui, como a ANP publicou, mas
-- não entram nas médias das tabelas de análise.

with coletas as (
    select * from {{ ref('stg_precos') }}
),

com_desvio as (

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
    round(preco_venda / median(preco_venda) over (partition by uf, produto, semana) - 1, 4)
        as desvio_mediana_uf,
    arquivo_origem
from coletas
)

select
    *,
    abs(desvio_mediana_uf) > 0.6 as fora_da_curva
from com_desvio
