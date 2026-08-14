import os
import tempfile
from collections.abc import Generator

import duckdb
import pytest

from src.engine.consensus_calc import (
    _inicializar_banco,
    gerar_carteira_consenso,
    salvar_resultados_parciais,
)


@pytest.fixture
def db_path() -> Generator[str, None, None]:
    """Fixture para criar um banco de dados temporário.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    fd, path = tempfile.mkstemp(suffix=".duckdb")
    os.close(fd)
    os.remove(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_inicializar_banco() -> None:
    """Testa a função _inicializar_banco.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    with duckdb.connect() as conn:
        _inicializar_banco(conn)
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        assert "raw_recomendacoes" in table_names
        assert "dados_mercado" in table_names


def test_salvar_recomendacoes(db_path: str) -> None:
    """Testa a função salvar_resultados_parciais.

    Args:
        db_path: Parâmetro de teste.

    Returns:
        None

    Raises:
        None
    """
    dados = [{"corretora": "XP", "tickers": ["PETR4", "VALE3"]}]
    salvar_resultados_parciais(dados, "2023-08", db_path)
    with duckdb.connect(db_path) as conn:
        res = conn.execute("SELECT * FROM raw_recomendacoes").fetchall()
        assert len(res) == 2


def test_calcular_consenso_db_vazio(db_path: str) -> None:
    """Testa a função calcular_consenso com DB vazio.

    Args:
        db_path: Parâmetro de teste.

    Returns:
        None

    Raises:
        None
    """
    with duckdb.connect(db_path) as conn:
        _inicializar_banco(conn)
    df = gerar_carteira_consenso(db_path).to_pandas()
    assert df.empty


def test_calcular_consenso_sucesso(db_path: str) -> None:
    """Testa a função calcular_consenso_sucesso.

    Args:
        db_path: Parâmetro de teste.

    Returns:
        None

    Raises:
        None
    """
    dados = [{"corretora": "XP", "tickers": ["PETR4"]}]
    salvar_resultados_parciais(dados, "2023-08", db_path)
    df = gerar_carteira_consenso(db_path).to_pandas()
    assert not df.empty
    assert "votos" in df.columns


def test_calcular_consenso_multiplas_corretoras(db_path: str) -> None:
    """Testa a função calcular_consenso_multiplas_corretoras.

    Args:
        db_path: Parâmetro de teste.

    Returns:
        None

    Raises:
        None
    """
    dados = [
        {"corretora": "XP", "tickers": ["PETR4"]},
        {"corretora": "BTG", "tickers": ["PETR4", "VALE3"]},
    ]
    salvar_resultados_parciais(dados, "2023-08", db_path)
    df = gerar_carteira_consenso(db_path).to_pandas()
    assert not df.empty
