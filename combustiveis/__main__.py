"""Linha de comando do pipeline.

    python -m combustiveis pipeline --desde 2025-1 --ate 2026-1   # baixa, carrega e transforma
    python -m combustiveis amostra                                # usa dados sintéticos, sem internet
    python -m combustiveis qualidade                              # descartes e valores fora da curva
    python -m combustiveis baixar | carregar | transformar
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from datetime import date

from . import amostra, carga, config, ingestao, qualidade


def transformar(banco=config.CAMINHO_BANCO) -> None:
    """Roda `dbt build` (modelos + testes de qualidade) no banco indicado."""
    comando = [
        config.DBT_BIN, "build",
        "--project-dir", str(config.DIR_DBT),
        "--profiles-dir", str(config.DIR_DBT),
    ]
    ambiente = {**os.environ, "ANP_BANCO": str(banco)}
    subprocess.run(comando, check=True, env=ambiente)  # CalledProcessError se modelo ou teste falhar


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    atual = str(ingestao.Semestre.de_data(date.today()))

    p = argparse.ArgumentParser(prog="combustiveis", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="comando", required=True)
    for nome in ("baixar", "pipeline"):
        s = sub.add_parser(nome)
        s.add_argument("--desde", default="2025-1", help="semestre inicial, ex.: 2025-1")
        s.add_argument("--ate", default=atual, help=f"semestre final (padrão: atual, {atual})")
        s.add_argument("--forcar", action="store_true", help="baixa de novo mesmo se já existir")
    sub.add_parser("carregar")
    sub.add_parser("transformar")
    sub.add_parser("amostra", help="gera dados sintéticos em data/amostra.duckdb, sem internet")
    q = sub.add_parser("qualidade", help="mostra por que linhas foram descartadas e o que foge da curva")
    q.add_argument("--amostra", action="store_true", help="analisa o banco da amostra")
    args = p.parse_args(argv)

    if args.comando in ("baixar", "pipeline"):
        arquivos = ingestao.baixar(
            ingestao.Semestre.de_texto(args.desde), ingestao.Semestre.de_texto(args.ate),
            forcar=args.forcar,
        )
        if args.comando == "pipeline":
            carga.carregar(arquivos)
            transformar()
    elif args.comando == "carregar":
        carga.carregar()
    elif args.comando == "transformar":
        transformar()
    elif args.comando == "amostra":
        arquivos = amostra.gerar_padrao(config.DIR_AMOSTRA)
        carga.carregar(arquivos, banco=config.BANCO_AMOSTRA)
        transformar(config.BANCO_AMOSTRA)
    elif args.comando == "qualidade":
        qualidade.relatorio(config.BANCO_AMOSTRA if args.amostra else config.CAMINHO_BANCO)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as erro:
        sys.exit(erro.returncode)
