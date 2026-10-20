"""Configuração central: caminhos e endereços, todos sobrescrevíveis por variável de ambiente."""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Onde ficam os arquivos baixados e o banco DuckDB.
DIR_DADOS = Path(os.getenv("ANP_DIR_DADOS", RAIZ / "data"))
DIR_BRUTO = DIR_DADOS / "bruto"
CAMINHO_BANCO = Path(os.getenv("ANP_BANCO", DIR_DADOS / "combustiveis.duckdb"))

# A amostra sintética fica separada, para nunca se misturar aos dados reais.
DIR_AMOSTRA = DIR_DADOS / "amostra"
BANCO_AMOSTRA = DIR_DADOS / "amostra.duckdb"

# Projeto dbt e o executável (no container do Airflow o dbt vive num ambiente separado).
DIR_DBT = RAIZ / "transformacao"
DBT_BIN = os.getenv("ANP_DBT_BIN", "dbt")

# Série histórica de preços de combustíveis automotivos (CA), publicada por semestre.
URL_BASE_ANP = os.getenv(
    "ANP_URL_BASE",
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/ca/",
)
