-- Quanto cada combustível subiu ou caiu em cada estado no período carregado.
-- Compara a média das 4 primeiras semanas com a das 4 últimas, para não depender
-- de uma semana isolada (que pode ter poucas coletas).

with semanal as (
    select * from {{ ref('preco_semanal_uf') }}
),

ordenado as (
    select
        *,
        dense_rank() over (partition by uf, produto order by semana)      as ordem_inicio,
        dense_rank() over (partition by uf, produto order by semana desc) as ordem_fim
    from semanal
)

select
    regiao,
    uf,
    produto,
    unidade,
    min(semana)                                                              as primeira_semana,
    max(semana)                                                              as ultima_semana,
    round(avg(preco_medio) filter (where ordem_inicio <= 4), 3)              as preco_inicio,
    round(avg(preco_medio) filter (where ordem_fim <= 4), 3)                 as preco_fim,
    round(
        avg(preco_medio) filter (where ordem_fim <= 4)
        / avg(preco_medio) filter (where ordem_inicio <= 4) - 1,
        4
    )                                                                        as variacao,
    count(*)                                                                 as semanas
from ordenado
group by all
having count(*) >= 8   -- com menos de 8 semanas a comparação não diz nada
