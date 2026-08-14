import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    """Configurações centrais do sistema."""

    # Ingestion / Discovery
    CARTEIRA_VALOR_URL: str = os.getenv("CARTEIRA_VALOR_URL", "https://infograficos.valor.globo.com/carteira-valor/")

    # System
    DB_PATH: str = os.getenv("DB_PATH", "quant_consensus_prod.duckdb")

    # Histórico
    ANO_INICIO_HISTORICO: int = 2022


settings = Settings()
