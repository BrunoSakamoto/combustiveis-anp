"""Ponta a ponta com a amostra: carga + dbt build (modelos e testes de qualidade)."""

import duckdb
import pytest

from combustiveis import amostra, carga
from combustiveis.__main__ import transformar


@pytest.fixture(scope="module")
def banco(tmp_path_factory):
    pasta = tmp_path_factory.mktemp("pipeline")
    caminho = pasta / "anp.duckdb"
    carga.carregar(amostra.gerar_padrao(pasta / "bruto"), banco=caminho)
    transformar(caminho)  # levanta CalledProcessError se algum modelo ou teste falhar
    return caminho


def test_tabelas_de_analise_existem(banco):
    with duckdb.connect(str(banco), read_only=True) as con:
        tabelas = {t for (t,) in con.execute(
            "select table_name from information_schema.tables where table_schema = 'analise'"
        ).fetchall()}
    assert {"fct_coletas", "preco_semanal_uf", "variacao_uf", "bandeiras"} <= tabelas


def test_staging_remove_duplicatas_e_tipa(banco):
    with duckdb.connect(str(banco), read_only=True) as con:
        bruto = con.execute("select count(*) from bruto.precos_ca").fetchone()[0]
        limpo, tipo = con.execute(
            "select count(*), any_value(typeof(preco_venda)) from staging.stg_precos"
        ).fetchone()
    assert 0 < limpo <= bruto
    assert tipo.startswith("DECIMAL")


def test_bandeira_branca_mais_barata_na_amostra(banco):
    """A amostra embute um desconto de 2,5% na bandeira branca; o modelo tem de encontrá-lo."""
    with duckdb.connect(str(banco), read_only=True) as con:
        diferenca = con.execute(
            "select diferenca_media from analise.bandeiras where produto = 'GASOLINA' and bandeira = 'BRANCA'"
        ).fetchone()[0]
    assert diferenca < 0
