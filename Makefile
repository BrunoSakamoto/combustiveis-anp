# Atalhos. No Windows sem make, rode os comandos da direita direto (veja o README).
.PHONY: instalar amostra pipeline painel testes lint airflow limpar

instalar:
	pip install -e ".[painel,dev]"

amostra:            ## dados sintéticos, sem internet
	python -m combustiveis amostra

pipeline:           ## baixa a série real da ANP, carrega e transforma
	python -m combustiveis pipeline --desde 2025-1

painel:
	streamlit run painel/app.py

testes:
	pytest -q

lint:
	ruff check .

airflow:            ## Airflow + painel em containers
	docker compose up --build

limpar:
	rm -rf data/*.duckdb data/amostra transformacao/target transformacao/logs
