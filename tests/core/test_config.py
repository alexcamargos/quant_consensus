"""Testes unitários para o módulo core.config."""

import os

from src.core.config import Settings


def test_settings_defaults() -> None:
    """Verifica os valores padrão da configuração."""
    settings = Settings()
    
    assert settings.CARTEIRA_VALOR_URL == "https://infograficos.valor.globo.com/carteira-valor/"
    assert settings.DB_PATH == "data/quant_consensus_prod.duckdb"
    assert settings.ANO_INICIO_HISTORICO == 2022
    assert settings.REQUEST_TIMEOUT == 15
    assert "User-Agent" in settings.DEFAULT_HEADERS
    assert "Mozilla/5.0" in settings.DEFAULT_HEADERS["User-Agent"]


def test_settings_env_override(monkeypatch) -> None:
    """Verifica se as variáveis de ambiente sobrescrevem os valores padrão."""
    import importlib
    import src.core.config
    
    monkeypatch.setenv("CARTEIRA_VALOR_URL", "https://example.com/carteira")
    monkeypatch.setenv("DB_PATH", "test_db.duckdb")
    
    # Reload do módulo para reavaliar os.getenv
    importlib.reload(src.core.config)
    settings = src.core.config.Settings()
    
    assert settings.CARTEIRA_VALOR_URL == "https://example.com/carteira"
    assert settings.DB_PATH == "test_db.duckdb"
