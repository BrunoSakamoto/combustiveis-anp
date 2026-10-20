-- Posto de bandeira branca é mesmo mais barato? Compara cada coleta com a média do
-- mesmo município, produto e semana, e resume por bandeira. Assim a diferença não é
-- efeito de a bandeira estar mais presente em cidades caras ou baratas.

select
    produto,
    bandeira,
    round(avg(desvio_media_municipio), 4)  as diferenca_media,
    count(*)                               as coletas,
    count(distinct cnpj)                   as postos
from {{ ref('fct_coletas') }}
where not fora_da_curva
group by all
having count(distinct cnpj) >= 5
