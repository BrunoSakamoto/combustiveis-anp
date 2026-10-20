"""Gera uma amostra SINTÉTICA no formato exato da série da ANP.

Serve para testes, CI e para rodar o projeto sem baixar nada. Os preços seguem níveis e
tendências plausíveis, mas não são dados reais: o painel avisa quando está mostrando a amostra.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

CABECALHO = [
    "Regiao - Sigla", "Estado - Sigla", "Municipio", "Revenda", "CNPJ da Revenda",
    "Nome da Rua", "Numero Rua", "Complemento", "Bairro", "Cep", "Produto",
    "Data da Coleta", "Valor de Venda", "Valor de Compra", "Unidade de Medida", "Bandeira",
]

# UF -> (região, municípios, fator de preço regional)
UFS = {
    "SP": ("SE", ["SAO PAULO", "CAMPINAS", "SOROCABA", "RIBEIRAO PRETO"], 0.98),
    "RJ": ("SE", ["RIO DE JANEIRO", "NITEROI"], 1.03),
    "MG": ("SE", ["BELO HORIZONTE", "UBERLANDIA"], 1.00),
    "PR": ("S", ["CURITIBA", "LONDRINA"], 1.00),
    "RS": ("S", ["PORTO ALEGRE"], 1.02),
    "BA": ("NE", ["SALVADOR", "FEIRA DE SANTANA"], 1.04),
    "PE": ("NE", ["RECIFE"], 1.03),
    "GO": ("CO", ["GOIANIA"], 0.99),
    "AM": ("N", ["MANAUS"], 1.09),
    "AC": ("N", ["RIO BRANCO"], 1.16),
}

# produto -> (preço base em R$, unidade, tendência por semana)
PRODUTOS = {
    "GASOLINA": (6.25, "R$ / litro", 0.0007),
    "GASOLINA ADITIVADA": (6.45, "R$ / litro", 0.0007),
    "ETANOL": (4.15, "R$ / litro", -0.0004),
    "DIESEL": (5.95, "R$ / litro", 0.0012),
    "DIESEL S10": (6.05, "R$ / litro", 0.0012),
    "GNV": (4.85, "R$ / m³", 0.0003),
}
BANDEIRAS = [("BRANCA", 0.975), ("IPIRANGA", 1.005), ("VIBRA ENERGIA", 1.01), ("RAIZEN", 1.008)]


def _cnpj(rng: random.Random) -> str:
    n = f"{rng.randrange(10**8):08d}0001{rng.randrange(100):02d}"
    return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"


def _postos(rng: random.Random) -> list[dict]:
    postos = []
    for uf, (regiao, municipios, _) in UFS.items():
        for municipio in municipios:
            for i in range(rng.randint(2, 4)):
                bandeira, _ = rng.choice(BANDEIRAS)
                postos.append({
                    "regiao": regiao, "uf": uf, "municipio": municipio,
                    "revenda": f"AUTO POSTO {municipio.split()[0]} {i + 1} LTDA",
                    "cnpj": _cnpj(rng), "bandeira": bandeira,
                    "rua": rng.choice(["AVENIDA BRASIL", "RUA XV DE NOVEMBRO", "RODOVIA SP-340"]),
                    "numero": str(rng.randint(10, 3000)),
                    "bairro": rng.choice(["CENTRO", "JARDIM AMERICA", "VILA NOVA"]),
                    "cep": f"{rng.randint(10000, 99999)}-{rng.randint(0, 999):03d}",
                    "produtos": rng.sample(list(PRODUTOS), k=rng.randint(3, 5)),
                })
    return postos


def gerar(destino: Path, ano: int, semestre: int, encoding: str = "utf-8-sig", semente: int = 7) -> Path:
    rng = random.Random(f"{semente}-{ano}-{semestre}")
    postos = _postos(random.Random(semente))  # mesmos postos em todos os semestres
    inicio = date(ano, 1 if semestre == 1 else 7, 1)
    fim = date(ano, 6, 30) if semestre == 1 else date(ano, 12, 31)
    semana0 = date(2025, 1, 6)
    fator_bandeira = dict(BANDEIRAS)

    linhas = [";".join(CABECALHO)]
    dia = inicio + timedelta(days=(7 - inicio.weekday()) % 7)  # primeira segunda-feira
    while dia <= fim:
        semanas = (dia - semana0).days // 7
        for posto in rng.sample(postos, k=len(postos) * 2 // 3):  # nem todo posto é visitado
            coleta = min(dia + timedelta(days=rng.randint(0, 3)), fim)
            for produto in posto["produtos"]:
                base, unidade, tendencia = PRODUTOS[produto]
                preco = (
                    base * (1 + tendencia * semanas) * UFS[posto["uf"]][2]
                    * fator_bandeira[posto["bandeira"]] * rng.uniform(0.97, 1.03)
                )
                linhas.append(";".join([
                    posto["regiao"], posto["uf"], posto["municipio"], posto["revenda"],
                    posto["cnpj"], posto["rua"], posto["numero"], "", posto["bairro"],
                    posto["cep"], produto, coleta.strftime("%d/%m/%Y"),
                    f"{preco:.2f}".replace(".", ","), "", unidade, posto["bandeira"],
                ]))
        dia += timedelta(days=7)

    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"ca-{ano}-{semestre:02d}.csv"
    caminho.write_text("\n".join(linhas) + "\n", encoding=encoding)
    return caminho


def gerar_padrao(destino: Path) -> list[Path]:
    """Dois semestres; um em UTF-8 com BOM e outro em Latin-1, como acontece nos arquivos reais."""
    return [
        gerar(destino, 2025, 2, encoding="latin-1"),
        gerar(destino, 2026, 1, encoding="utf-8-sig"),
    ]
