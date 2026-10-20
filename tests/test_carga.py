import duckdb
import pytest

from combustiveis import amostra, carga

CABECALHO_ACENTUADO = (
    "Região - Sigla;Estado - Sigla;Município;Revenda;CNPJ da Revenda;Nome da Rua;Número Rua;"
    "Complemento;Bairro;Cep;Produto;Data da Coleta;Valor de Venda;Valor de Compra;"
    "Unidade de Medida;Bandeira"
)


def _contar(banco, arquivo=None):
    with duckdb.connect(str(banco)) as con:
        if arquivo:
            return con.execute(
                "select count(*) from bruto.precos_ca where _arquivo = ?", [arquivo]
            ).fetchone()[0]
        return con.execute("select count(*) from bruto.precos_ca").fetchone()[0]


def test_mapeia_cabecalho_com_e_sem_acento():
    mapa = carga.mapear_cabecalho(CABECALHO_ACENTUADO.split(";"))
    assert mapa["Município"] == "municipio"
    assert mapa["Estado - Sigla"] == "uf"
    assert mapa["Valor de Venda"] == "valor_venda"


def test_cabecalho_sem_coluna_essencial_falha():
    with pytest.raises(ValueError, match="valor_venda"):
        carga.mapear_cabecalho(
            ["Estado - Sigla", "Municipio", "CNPJ da Revenda", "Produto", "Data da Coleta"]
        )


def test_carrega_latin1_e_utf8_com_bom(tmp_path):
    arquivos = amostra.gerar_padrao(tmp_path / "bruto")
    assert arquivos[0].read_bytes()[:3] != b"\xef\xbb\xbf"  # latin-1
    assert arquivos[1].read_bytes()[:3] == b"\xef\xbb\xbf"  # utf-8 com BOM
    banco = tmp_path / "t.duckdb"
    carga.carregar(arquivos, banco=banco)
    with duckdb.connect(str(banco)) as con:
        unidades = {u for (u,) in con.execute("select distinct unidade from bruto.precos_ca").fetchall()}
    assert "R$ / m³" in unidades  # o "³" sobreviveu aos dois encodings


def test_carregar_duas_vezes_nao_duplica(tmp_path):
    arquivos = amostra.gerar_padrao(tmp_path / "bruto")
    banco = tmp_path / "t.duckdb"
    primeira = carga.carregar(arquivos, banco=banco)
    segunda = carga.carregar(arquivos, banco=banco)
    assert primeira > 0 and segunda == 0
    assert _contar(banco) == primeira


def test_arquivo_alterado_substitui_as_linhas_antigas(tmp_path):
    csv = tmp_path / "ca-2026-01.csv"
    linha = (
        "SE;SP;CAMPINAS;POSTO;12.345.678/0001-90;RUA A;1;;CENTRO;13000-000;"
        "GASOLINA;05/01/2026;{};;R$ / litro;BRANCA"
    )
    csv.write_text(CABECALHO_ACENTUADO + "\n" + linha.format("6,19") + "\n", encoding="utf-8")
    banco = tmp_path / "t.duckdb"
    carga.carregar([csv], banco=banco)

    csv.write_text(
        CABECALHO_ACENTUADO + "\n" + linha.format("6,29") + "\n" + linha.format("6,39") + "\n",
        encoding="utf-8",
    )
    carga.carregar([csv], banco=banco)
    assert _contar(banco, "ca-2026-01.csv") == 2
