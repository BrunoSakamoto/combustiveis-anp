-- A chave de uma coleta é (posto, produto, dia). Qualquer linha devolvida aqui é duplicata.
select cnpj, produto, data_coleta, count(*) as vezes
from {{ ref('stg_precos') }}
group by all
having count(*) > 1
