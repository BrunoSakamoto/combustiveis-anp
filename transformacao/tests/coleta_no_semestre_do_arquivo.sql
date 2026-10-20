-- Uma coleta do arquivo ca-2025-02 tem de ser do 2º semestre de 2025.
-- Pega arquivo trocado ou data lida no formato errado (dia e mês invertidos).
{{ config(severity='warn') }}

select arquivo_origem, data_coleta
from {{ ref('stg_precos') }}
where regexp_matches(arquivo_origem, '^ca-\d{4}-0[12]\.csv$')
  and (
      year(data_coleta) <> cast(substr(arquivo_origem, 4, 4) as integer)
      or (case when month(data_coleta) <= 6 then 1 else 2 end)
         <> cast(substr(arquivo_origem, 10, 1) as integer)
  )
