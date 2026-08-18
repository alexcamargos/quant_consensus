import os
from dataclasses import dataclass, field
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

    # HTTP / Scraping
    REQUEST_TIMEOUT: int = 15
    DEFAULT_HEADERS: dict[str, str] = field(default_factory=lambda: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    })


settings = Settings()
