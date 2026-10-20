FROM apache/airflow:3.3.2-python3.12

# Dependências das tarefas, junto do Airflow (versão fixada para o pip não trocá-la).
RUN pip install --no-cache-dir "apache-airflow==3.3.2" "duckdb>=1.4,<2" "requests>=2.32,<3"

# O dbt fica num ambiente separado: as dependências dele conflitam com as do Airflow.
RUN python -m venv /home/airflow/dbt-venv \
 && /home/airflow/dbt-venv/bin/pip install --no-cache-dir "dbt-duckdb>=1.10,<2"
