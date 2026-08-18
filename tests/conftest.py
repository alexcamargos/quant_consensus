"""Configurações compartilhadas (fixtures) para os testes do quant_consensus."""

import os
import tempfile
from collections.abc import Generator

import pytest


@pytest.fixture
def db_path() -> Generator[str, None, None]:
    """Cria um banco de dados temporário DuckDB.

    Yields:
        str: Caminho absoluto para o arquivo de banco de dados temporário.
    """
    fd, path = tempfile.mkstemp(suffix=".duckdb")
    os.close(fd)
    os.remove(path)
    
    yield path
    
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
