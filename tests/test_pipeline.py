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


def test_relatorio_de_qualidade_roda(banco, capsys):
    from combustiveis import qualidade

    qualidade.relatorio(banco)
    saida = capsys.readouterr().out
    assert "ca-2026-01.csv" in saida            # a tabela de descartes lista os arquivos
    assert "fora da curva" in saida             # e a seção de coletas fora da curva aparece


def test_linhas_vazias_nao_viram_registro(banco):
    with duckdb.connect(str(banco), read_only=True) as con:
        vazias = con.execute(
            "select count(*) from bruto.precos_ca "
            "where coalesce(uf, municipio, cnpj, produto, data_coleta, valor_venda) is null"
        ).fetchone()[0]
        restantes = con.execute(
            "select count(*) from staging.stg_precos where uf is null"
        ).fetchone()[0]
    assert vazias == 50   # 25 por arquivo da amostra
    assert restantes == 0


def test_coleta_fora_da_curva_e_marcada_e_fica_fora_das_medias(banco):
    with duckdb.connect(str(banco), read_only=True) as con:
        marcadas = con.execute(
            "select count(*) from analise.fct_coletas where fora_da_curva"
        ).fetchone()[0]
        maior_media_etanol_sp = con.execute(
            "select max(preco_maximo) from analise.preco_semanal_uf where uf = 'SP' and produto = 'ETANOL'"
        ).fetchone()[0]
    assert marcadas >= 1
    assert maior_media_etanol_sp < 6.89   # o etanol a R$ 6,89 não entrou nas agregações
