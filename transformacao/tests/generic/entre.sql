{# Falha para cada linha cujo valor está fora de [minimo, maximo]. #}
{% test entre(model, column_name, minimo, maximo) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} < {{ minimo }} or {{ column_name }} > {{ maximo }}
{% endtest %}
