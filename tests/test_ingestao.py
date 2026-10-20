from datetime import date

import pytest

from combustiveis import ingestao
from combustiveis.ingestao import Semestre


def test_intervalo_atravessa_o_ano():
    assert ingestao.intervalo(Semestre(2024, 2), Semestre(2025, 2)) == [
        Semestre(2024, 2), Semestre(2025, 1), Semestre(2025, 2)
    ]


def test_intervalo_invertido_falha():
    with pytest.raises(ValueError):
        ingestao.intervalo(Semestre(2026, 1), Semestre(2025, 1))


@pytest.mark.parametrize("texto, esperado", [("2025-1", Semestre(2025, 1)), ("2025-02", Semestre(2025, 2))])
def test_semestre_de_texto(texto, esperado):
    assert Semestre.de_texto(texto) == esperado


def test_semestre_invalido():
    with pytest.raises(ValueError):
        Semestre.de_texto("2025-3")


@pytest.mark.parametrize(
    "semestre, final",
    [
        (Semestre(2026, 1), "ca-2026-01.zip"),
        (Semestre(2022, 2), "ca-2022-02.zip"),
        (Semestre(2022, 1), "precos-semestrais-ca.zip"),  # exceção no padrão da ANP
        (Semestre(2021, 2), "ca-2021-02.csv"),            # até 2021 os arquivos são CSV
    ],
)
def test_url_segue_as_excecoes_da_anp(semestre, final):
    assert ingestao.url_do_semestre(semestre, base="https://x/").endswith("/" + final)


@pytest.fixture
def downloads(monkeypatch):
    """Substitui o download real por um que só registra a chamada e escreve um CSV."""
    chamadas = []

    def falso(url, destino, tentativas=3):
        chamadas.append(url)
        destino.write_text("Produto;Valor de Venda\n")

    monkeypatch.setattr(ingestao, "_baixar", falso)
    monkeypatch.setattr(ingestao, "url_do_semestre", lambda s: f"https://x/{s.nome}.csv")
    return chamadas


def test_semestre_antigo_nao_e_baixado_duas_vezes(tmp_path, downloads):
    hoje = date(2026, 10, 20)
    ingestao.baixar_semestre(Semestre(2025, 1), dir_bruto=tmp_path, hoje=hoje)
    ingestao.baixar_semestre(Semestre(2025, 1), dir_bruto=tmp_path, hoje=hoje)
    assert len(downloads) == 1


def test_semestre_corrente_e_sempre_baixado_de_novo(tmp_path, downloads):
    hoje = date(2026, 10, 20)
    ingestao.baixar_semestre(Semestre(2026, 2), dir_bruto=tmp_path, hoje=hoje)
    ingestao.baixar_semestre(Semestre(2026, 2), dir_bruto=tmp_path, hoje=hoje)
    assert len(downloads) == 2


@pytest.fixture
def anp_sem_o_arquivo(monkeypatch):
    def nao_publicado(url, destino, tentativas=3):
        raise ingestao.NaoPublicado(url)

    monkeypatch.setattr(ingestao, "_baixar", nao_publicado)


def test_semestre_recente_ainda_nao_publicado_e_pulado(tmp_path, anp_sem_o_arquivo):
    caminho = ingestao.baixar_semestre(Semestre(2026, 2), dir_bruto=tmp_path, hoje=date(2026, 10, 20))
    assert caminho is None


def test_semestre_antigo_sem_arquivo_e_erro(tmp_path, anp_sem_o_arquivo):
    with pytest.raises(ingestao.NaoPublicado):
        ingestao.baixar_semestre(Semestre(2024, 1), dir_bruto=tmp_path, hoje=date(2026, 10, 20))
