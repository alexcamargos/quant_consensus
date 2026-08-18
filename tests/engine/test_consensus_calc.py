"""Testes unitários para o módulo engine.consensus_calc."""

import os
from unittest import mock

import duckdb
import pytest

from src.engine.consensus_calc import (
    _inicializar_banco,
    gerar_carteira_consenso,
    obter_meses_salvos,
    salvar_resultados_parciais,
)


def test_inicializar_banco() -> None:
    """Verifica se a inicialização cria as tabelas e views corretamente."""
    with duckdb.connect() as conn:
        _inicializar_banco(conn)
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        
        assert "raw_recomendacoes" in table_names
        assert "dados_mercado" in table_names
        assert "vw_dados_corretoras" in table_names
        assert "vw_corretoras_por_mes" in table_names
        assert "vw_carteira_consolidada" in table_names
        assert "vw_alteracoes_carteira" in table_names


def test_salvar_recomendacoes_vazias(db_path: str, mocker) -> None:
    """Verifica o comportamento ao tentar salvar uma lista vazia de dados."""
    mock_logger = mocker.patch("src.engine.consensus_calc.logger")
    salvar_resultados_parciais([], "2023-08", db_path)
    
    mock_logger.warning.assert_called_with("Nenhum dado estruturado para salvar.")


def test_salvar_recomendacoes_nova(db_path: str) -> None:
    """Verifica salvar recomendações com exclusão prévia (append=False)."""
    dados = [{"corretora": "XP", "tickers": ["PETR4", "VALE3"]}]
    salvar_resultados_parciais(dados, "2023-08", db_path)
    
    with duckdb.connect(db_path) as conn:
        res = conn.execute("SELECT * FROM raw_recomendacoes").fetchall()
        assert len(res) == 2


def test_salvar_recomendacoes_append(db_path: str) -> None:
    """Verifica adicionar recomendações mantendo os dados anteriores (append=True)."""
    dados_iniciais = [{"corretora": "XP", "tickers": ["PETR4"]}]
    salvar_resultados_parciais(dados_iniciais, "2023-08", db_path)
    
    dados_novos = [{"corretora": "BTG", "tickers": ["VALE3"]}]
    salvar_resultados_parciais(dados_novos, "2023-09", db_path, append=True)
    
    with duckdb.connect(db_path) as conn:
        res = conn.execute("SELECT corretora, ticker, mes_ref FROM raw_recomendacoes").fetchall()
        assert len(res) == 2
        # Verifica se ambos os dados estão presentes
        assert ("XP", "PETR4", "2023-08") in res
        assert ("BTG", "VALE3", "2023-09") in res


def test_obter_meses_salvos_db_inexistente() -> None:
    """Verifica a obtenção de meses salvos quando o banco de dados não existe."""
    # Garante que não está usando um banco existente
    resultado = obter_meses_salvos("caminho_inexistente_banco.duckdb")
    assert resultado == set()


def test_obter_meses_salvos_tabela_inexistente(db_path: str) -> None:
    """Verifica a obtenção de meses quando o DB existe, mas a tabela raw_recomendacoes não."""
    # Para passar no os.path.exists, criamos o arquivo e conectamos no duckdb
    with duckdb.connect(db_path) as conn:
        pass  # Apenas cria o banco vazio
        
    resultado = obter_meses_salvos(db_path)
    assert resultado == set()


def test_obter_meses_salvos_sucesso(db_path: str) -> None:
    """Verifica se retorna corretamente os meses armazenados no banco de dados."""
    dados = [
        {"corretora": "XP", "tickers": ["PETR4"]},
    ]
    salvar_resultados_parciais(dados, "2023-08", db_path)
    salvar_resultados_parciais(dados, "2023-09", db_path, append=True)
    
    meses = obter_meses_salvos(db_path)
    assert meses == {"2023-08", "2023-09"}


def test_calcular_consenso_db_vazio(db_path: str) -> None:
    """Verifica o cálculo de consenso em um banco de dados vazio (sem dados)."""
    with duckdb.connect(db_path) as conn:
        _inicializar_banco(conn)
        
    df = gerar_carteira_consenso(db_path).to_pandas()
    assert df.empty


def test_calcular_consenso_sucesso(db_path: str) -> None:
    """Verifica o cálculo de consenso de um mês específico com sucesso."""
    dados = [{"corretora": "XP", "tickers": ["PETR4"]}]
    salvar_resultados_parciais(dados, "2023-08", db_path)
    
    df = gerar_carteira_consenso(db_path, mes_ref="2023-08").to_pandas()
    assert not df.empty
    assert "votos" in df.columns
    assert df.iloc[0]["ticker"] == "PETR4"
    assert df.iloc[0]["votos"] == 1


def test_calcular_consenso_multiplas_corretoras(db_path: str) -> None:
    """Verifica o cálculo de consenso somando os votos de múltiplas corretoras."""
    dados = [
        {"corretora": "XP", "tickers": ["PETR4"]},
        {"corretora": "BTG", "tickers": ["PETR4", "VALE3"]},
    ]
    salvar_resultados_parciais(dados, "2023-08", db_path)
    
    df = gerar_carteira_consenso(db_path, mes_ref="2023-08").to_pandas()
    assert not df.empty
    
    # PETR4 recebeu dois votos, VALE3 recebeu um
    row_petr = df[df["ticker"] == "PETR4"].iloc[0]
    row_vale = df[df["ticker"] == "VALE3"].iloc[0]
    
    assert row_petr["votos"] == 2
    assert row_vale["votos"] == 1
    
    # A ordenação pelo rank deve garantir PETR4 primeiro (pois tem mais votos)
    assert df.iloc[0]["ticker"] == "PETR4"
    assert df.iloc[1]["ticker"] == "VALE3"


def test_calcular_consenso_todos_meses(db_path: str) -> None:
    """Verifica a geração do consenso consolidando todos os meses (mes_ref=None)."""
    dados = [{"corretora": "XP", "tickers": ["PETR4"]}]
    salvar_resultados_parciais(dados, "2023-08", db_path)
    salvar_resultados_parciais(dados, "2023-09", db_path, append=True)
    
    df = gerar_carteira_consenso(db_path).to_pandas()
    assert not df.empty
    assert len(df) == 2  # PETR4 em 2023-08 e PETR4 em 2023-09
