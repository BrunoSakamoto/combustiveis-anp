-- Avisa se a limpeza do staging descartou mais de 2% das linhas de algum arquivo:
-- costuma ser sinal de que a ANP mudou o formato (separador decimal, data, coluna).
{{ config(severity='warn') }}

with bruto as (
    select _arquivo as arquivo, count(*) as linhas_bruto
    from {{ source('bruto', 'precos_ca') }}
    group by 1
),
limpo as (
    select arquivo_origem as arquivo, count(*) as linhas_limpas
    from {{ ref('stg_precos') }}
    group by 1
)
select
    b.arquivo,
    b.linhas_bruto,
    coalesce(l.linhas_limpas, 0) as linhas_limpas,
    round(1 - coalesce(l.linhas_limpas, 0) / b.linhas_bruto, 4) as proporcao_descartada
from bruto b
left join limpo l using (arquivo)
where 1 - coalesce(l.linhas_limpas, 0) / b.linhas_bruto > 0.02
