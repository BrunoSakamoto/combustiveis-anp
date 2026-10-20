"""DAG mensal: baixa a série da ANP, carrega no DuckDB e roda o dbt (modelos + testes).

A ANP atualiza o semestre corrente uma vez por mês. Por isso a DAG roda mensalmente e
sempre rebaixa o semestre atual e o anterior; semestres antigos não mudam e são pulados
pela própria ingestão. Toda a lógica vive no pacote `combustiveis`: a DAG só orquestra,
então o mesmo pipeline roda igual pela linha de comando e no CI.

As tarefas rodam em sequência de propósito: o DuckDB aceita um único processo escrevendo.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.sdk import dag, task

PADRAO = {
    "owner": "bruno",
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}


@dag(
    dag_id="combustiveis_anp",
    description="Série histórica de preços de combustíveis da ANP → DuckDB → dbt",
    schedule="0 9 16 * *",  # dia 16 de cada mês, depois da atualização mensal da ANP
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=PADRAO,
    tags=["anp", "dbt", "duckdb"],
)
def combustiveis_anp():
    @task
    def baixar(data_interval_end=None) -> list[str]:
        """Semestre da execução e o anterior (que pode ter recebido correções)."""
        from datetime import date

        from combustiveis import ingestao

        referencia = data_interval_end.date() if data_interval_end else date.today()
        atual = ingestao.Semestre.de_data(referencia)
        anterior = (
            ingestao.Semestre(atual.ano - 1, 2) if atual.numero == 1
            else ingestao.Semestre(atual.ano, 1)
        )
        caminhos = ingestao.baixar(anterior, atual, forcar=True)
        return [str(c) for c in caminhos]

    @task
    def carregar(arquivos: list[str]) -> int:
        from pathlib import Path

        from combustiveis import carga

        return carga.carregar([Path(a) for a in arquivos])

    @task
    def transformar(linhas: int) -> None:
        """`dbt build`: falha a DAG se algum teste de qualidade com severidade error quebrar."""
        from combustiveis.__main__ import transformar as dbt_build

        dbt_build()

    transformar(carregar(baixar()))


combustiveis_anp()
