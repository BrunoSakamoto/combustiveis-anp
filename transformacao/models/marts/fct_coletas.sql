-- Fato principal: cada coleta, com o desvio do preço em relação à média do município
-- naquela semana. É a base para comparar bandeiras e achar postos fora da curva.
--
-- `fora_da_curva` marca coletas com preço provavelmente errado na origem (ex.: etanol
-- registrado com preço de gasolina). Elas continuam aqui, como a ANP publicou, mas não
-- entram nas médias das tabelas de análise. Uma coleta é marcada quando está mais de 60%
-- longe da mediana do ESTADO na semana E também da mediana do MUNICÍPIO:
--   - mediana, porque um valor errado não a desloca (a média, sim);
--   - o estado sozinho não basta: em estados grandes uma cidade distante pode ser bem mais
--     cara (ex.: Santarém no Pará), e se vários postos dela concordam, é preço local;
--   - o município sozinho também não: com menos de 3 coletas na semana não há como saber
--     qual valor está errado, então nesse caso vale só o critério do estado.

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
    round(preco_venda / median(preco_venda) over (partition by municipio, uf, produto, semana) - 1, 4)
        as desvio_mediana_municipio,
    count(*) over (partition by municipio, uf, produto, semana) as coletas_municipio,
    arquivo_origem
from coletas
)

select
    * exclude (desvio_mediana_municipio, coletas_municipio),
    abs(desvio_mediana_uf) > 0.6
    and (coletas_municipio < 3 or abs(desvio_mediana_municipio) > 0.6) as fora_da_curva
from com_desvio
