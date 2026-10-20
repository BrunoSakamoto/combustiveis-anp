-- Uma linha por coleta de preço: tipada, padronizada e sem duplicatas.
-- Linhas sem preço válido são descartadas aqui (e contadas no teste `descartes_staging`).

with origem as (
    select * from {{ source('bruto', 'precos_ca') }}
),

tipado as (
    select
        upper(trim(regiao))                                         as regiao,
        upper(trim(uf))                                             as uf,
        upper(trim(municipio))                                      as municipio,
        trim(revenda)                                               as revenda,
        regexp_replace(cnpj, '[^0-9]', '', 'g')                     as cnpj,
        upper(regexp_replace(trim(produto), '\s+', ' ', 'g'))       as produto,
        try_strptime(data_coleta, '%d/%m/%Y')::date                 as data_coleta,
        try_cast(replace(valor_venda, ',', '.') as decimal(8, 3))   as preco_venda,
        case when unidade ilike '%m%3%' or unidade ilike '%m³%'
             then 'm3' else 'litro' end                             as unidade,
        coalesce(nullif(upper(trim(bandeira)), ''), 'NAO INFORMADA') as bandeira,
        _arquivo                                                    as arquivo_origem,
        _carregado_em                                               as carregado_em
    from origem
)

select
    *,
    date_trunc('week', data_coleta)::date as semana
from tipado
where preco_venda > 0
  and data_coleta is not null
  and cnpj <> ''
-- O mesmo posto, produto e dia pode aparecer duas vezes (reenvio da ANP): fica o mais recente.
qualify row_number() over (
    partition by cnpj, produto, data_coleta
    order by carregado_em desc, preco_venda desc
) = 1
