-- Preço por semana, estado e produto: a série que o painel desenha.

select
    semana,
    regiao,
    uf,
    produto,
    unidade,
    round(avg(preco_venda), 3)                                  as preco_medio,
    round(median(preco_venda), 3)                               as preco_mediano,
    min(preco_venda)                                            as preco_minimo,
    max(preco_venda)                                            as preco_maximo,
    count(*)                                                    as coletas,
    count(distinct cnpj)                                        as postos
from {{ ref('fct_coletas') }}
where not fora_da_curva
group by all
