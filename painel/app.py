"""Painel: três perguntas sobre o preço dos combustíveis, lidas das tabelas do dbt.

    streamlit run painel/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from combustiveis import config  # noqa: E402

TINTA, MENTA, LARANJA, CINZA = "#111111", "#2f9e44", "#e8590c", "#adb5bd"
st.set_page_config(page_title="Combustíveis ANP", layout="wide")
px.defaults.template = "simple_white"


def escolher_banco() -> tuple[Path, bool]:
    if config.CAMINHO_BANCO.exists():
        return config.CAMINHO_BANCO, False
    if config.BANCO_AMOSTRA.exists():
        return config.BANCO_AMOSTRA, True
    st.error(
        "Nenhum banco encontrado. Rode `python -m combustiveis pipeline` (dados reais) "
        "ou `python -m combustiveis amostra` (dados sintéticos, sem internet)."
    )
    st.stop()


def br(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def pct(valor: float) -> str:
    return f"{valor:+.1%}".replace(".", ",")


@st.cache_data(ttl=600)
def consultar(banco: str, sql: str) -> pd.DataFrame:
    with duckdb.connect(banco, read_only=True) as con:
        return con.execute(sql).df()


banco, eh_amostra = escolher_banco()
q = lambda sql: consultar(str(banco), sql)  # noqa: E731

try:
    semanal = q("select * from analise.preco_semanal_uf")
    variacao = q("select * from analise.variacao_uf")
    bandeiras = q("select * from analise.bandeiras")
except duckdb.IOException:
    # O DuckDB aceita um processo escrevendo por vez; durante uma execução do pipeline o painel espera.
    st.info("O pipeline está atualizando os dados agora. Recarregue a página em alguns segundos.")
    st.stop()
except duckdb.CatalogException:
    st.error("O banco existe, mas as tabelas de análise não. Rode `python -m combustiveis transformar`.")
    st.stop()

st.title("Preço dos combustíveis no Brasil")
if eh_amostra:
    st.warning(
        "Exibindo a **amostra sintética** gerada pelo projeto, não dados reais da ANP. "
        "Rode `python -m combustiveis pipeline` para carregar a série oficial."
    )

periodo = f"{semanal.semana.min():%d/%m/%Y} a {semanal.semana.max():%d/%m/%Y}"
st.caption(
    f"Série histórica de preços da ANP, {periodo}. "
    f"{int(semanal.coletas.sum()):,} coletas em {semanal.uf.nunique()} estados.".replace(",", ".")
)

produtos = sorted(semanal.produto.unique())
produto = st.segmented_control(
    "Combustível", produtos, default="GASOLINA" if "GASOLINA" in produtos else produtos[0]
) or produtos[0]
unidade = "R$/m³" if produto == "GNV" else "R$/litro"

# 1. Quanto subiu e onde
st.header(f"Onde o preço da {produto.lower()} mais mudou")
v = variacao[variacao.produto == produto].sort_values("variacao", ascending=False)
if v.empty:
    st.info("Período curto demais para comparar (são precisas ao menos 8 semanas).")
else:
    topo = v.iloc[0]
    st.write(
        f"**{topo.uf}** teve a maior variação: de R\\$ {br(topo.preco_inicio)} para "
        f"R\\$ {br(topo.preco_fim)} ({pct(topo.variacao)}), comparando as 4 primeiras e as "
        f"4 últimas semanas do período."
    )
    cores = [LARANJA if x > 0 else MENTA for x in v.variacao]
    fig = px.bar(v, x="uf", y="variacao", text=v.variacao.map(pct))
    fig.update_traces(marker_color=cores, textposition="outside", cliponaxis=False)
    fig.update_layout(yaxis_tickformat=".0%", yaxis_title="Variação no período", xaxis_title=None,
                      height=360, margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

# 2. A série semanal
st.header("Semana a semana, por estado")
ufs = sorted(semanal.uf.unique())
padrao = [u for u in ("SP", "RJ", "BA", "AM") if u in ufs] or ufs[:3]
escolhidas = st.multiselect("Estados", ufs, default=padrao)
s = semanal[(semanal.produto == produto) & semanal.uf.isin(escolhidas)].sort_values("semana")
fig = px.line(s, x="semana", y="preco_medio", color="uf",
              labels={"semana": "", "preco_medio": unidade, "uf": "Estado"})
fig.update_layout(height=380, margin=dict(t=10, b=10), hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# 3. Bandeira branca é mais barata?
st.header("Bandeira branca é mais barata?")
b = bandeiras[bandeiras.produto == produto].sort_values("diferenca_media")
if b.empty:
    st.info("Poucos postos por bandeira para comparar este combustível.")
else:
    st.write(
        "Cada coleta é comparada com a média dos outros postos do mesmo município, na mesma "
        "semana. Assim a diferença não é efeito de uma bandeira estar mais em cidades caras."
    )
    cores = [MENTA if x < 0 else CINZA for x in b.diferenca_media]
    fig = px.bar(b, x="diferenca_media", y="bandeira", orientation="h",
                 text=b.diferenca_media.map(pct))
    fig.update_traces(marker_color=cores, textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_tickformat=".1%", xaxis_title="Diferença para a média do município",
                      yaxis_title=None, height=60 + 48 * len(b), margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

st.caption("Fonte: ANP, Série Histórica de Preços de Combustíveis. Código: github.com/BrunoSakamoto")
