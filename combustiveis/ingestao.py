"""Download da série histórica de preços da ANP, um arquivo por semestre.

Regras:
- Idempotente: um semestre já baixado não é baixado de novo, exceto o semestre corrente,
  que a ANP atualiza todo mês (ou quando `forcar=True`).
- O que chega em zip é extraído; o CSV final fica em `data/bruto/ca-AAAA-SS.csv`.
"""

from __future__ import annotations

import logging
import shutil
import time
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests

from . import config

log = logging.getLogger(__name__)


@dataclass(frozen=True, order=True)
class Semestre:
    ano: int
    numero: int  # 1 ou 2

    @classmethod
    def de_texto(cls, texto: str) -> Semestre:
        """Aceita '2025-1', '2025-01' ou '2025-2'."""
        ano, numero = texto.split("-")
        sem = cls(int(ano), int(numero))
        if sem.numero not in (1, 2):
            raise ValueError(f"Semestre inválido: {texto!r} (use AAAA-1 ou AAAA-2)")
        return sem

    @classmethod
    def de_data(cls, d: date) -> Semestre:
        return cls(d.year, 1 if d.month <= 6 else 2)

    def seguinte(self) -> Semestre:
        return Semestre(self.ano, 2) if self.numero == 1 else Semestre(self.ano + 1, 1)

    @property
    def nome(self) -> str:
        return f"ca-{self.ano}-{self.numero:02d}"

    def __str__(self) -> str:
        return f"{self.ano}-{self.numero}"


def intervalo(desde: Semestre, ate: Semestre) -> list[Semestre]:
    if desde > ate:
        raise ValueError(f"'desde' ({desde}) é depois de 'ate' ({ate})")
    atual, saida = desde, []
    while atual <= ate:
        saida.append(atual)
        atual = atual.seguinte()
    return saida


def url_do_semestre(sem: Semestre, base: str = config.URL_BASE_ANP) -> str:
    """O padrão de nome da ANP tem exceções históricas; elas ficam todas aqui."""
    if sem == Semestre(2022, 1):
        return base + "precos-semestrais-ca.zip"
    if sem.ano <= 2021:
        return base + f"{sem.nome}.csv"
    return base + f"{sem.nome}.zip"


def _baixar(url: str, destino: Path, tentativas: int = 3) -> None:
    temporario = destino.with_suffix(destino.suffix + ".parcial")
    for tentativa in range(1, tentativas + 1):
        try:
            with requests.get(url, stream=True, timeout=(10, 120)) as resp:
                resp.raise_for_status()
                with open(temporario, "wb") as f:
                    for bloco in resp.iter_content(chunk_size=1 << 20):
                        f.write(bloco)
            temporario.replace(destino)  # só aparece com o nome final quando completo
            return
        except requests.RequestException as erro:
            log.warning("Falha ao baixar %s (tentativa %d/%d): %s", url, tentativa, tentativas, erro)
            if tentativa == tentativas:
                temporario.unlink(missing_ok=True)
                raise
            time.sleep(2**tentativa)


def _extrair_csv(zip_path: Path, destino: Path) -> None:
    with zipfile.ZipFile(zip_path) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(csvs) != 1:
            raise ValueError(f"Esperava 1 CSV em {zip_path.name}, encontrei {len(csvs)}: {csvs}")
        with z.open(csvs[0]) as origem, open(destino, "wb") as saida:
            shutil.copyfileobj(origem, saida)


def baixar_semestre(
    sem: Semestre,
    dir_bruto: Path = config.DIR_BRUTO,
    forcar: bool = False,
    hoje: date | None = None,
) -> Path:
    """Garante `dir_bruto/ca-AAAA-SS.csv` e devolve o caminho."""
    dir_bruto.mkdir(parents=True, exist_ok=True)
    csv = dir_bruto / f"{sem.nome}.csv"
    corrente = sem == Semestre.de_data(hoje or date.today())

    if csv.exists() and not forcar and not corrente:
        log.info("%s já existe, pulando", csv.name)
        return csv

    url = url_do_semestre(sem)
    log.info("Baixando %s", url)
    if url.endswith(".zip"):
        zip_path = dir_bruto / f"{sem.nome}.zip"
        _baixar(url, zip_path)
        _extrair_csv(zip_path, csv)
        zip_path.unlink()
    else:
        _baixar(url, csv)
    return csv


def baixar(desde: Semestre, ate: Semestre, **kwargs) -> list[Path]:
    return [baixar_semestre(s, **kwargs) for s in intervalo(desde, ate)]
