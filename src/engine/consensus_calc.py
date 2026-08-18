"""Módulo responsável pelo cálculo de consenso utilizando DuckDB.

Focado em performance utilizando Pandas, PyArrow e operações vetorizadas via DuckDB.
"""

from typing import Any

import duckdb
import pandas as pd
import pyarrow as pa
from loguru import logger


def _inicializar_banco(conn: duckdb.DuckDBPyConnection) -> None:
    """Inicializa as tabelas necessárias no banco de dados DuckDB.

    Cria a tabela raw_recomendacoes e a tabela fictícia dados_mercado.
    """
    logger.debug("Inicializando schema do banco de dados (se não existir)...")

    # Tabela principal de recomendações da Sprint 1 e 2
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_recomendacoes (
            corretora VARCHAR,
            ticker VARCHAR,
            mes_ref VARCHAR
        )
    """)

    # Tabela fictícia de dados de mercado usada para critério de desempate
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dados_mercado (
            ticker VARCHAR PRIMARY KEY,
            volume_medio_diario BIGINT
        )
    """)

    # Inserindo dados fictícios de volume financeiro diário para testar o desempate
    conn.execute("""
        INSERT OR IGNORE INTO dados_mercado (ticker, volume_medio_diario)
        VALUES
            ('PETR4', 1500000000),
            ('VALE3', 1200000000),
            ('ITUB4', 900000000),
            ('BBAS3', 600000000),
            ('WEGE3', 400000000),
            ('RENT3', 350000000),
            ('SUZB3', 250000000),
            ('AXIA3', 100000000)
    """)

    # View para consultar dados por corretora
    conn.execute("""
        CREATE OR REPLACE VIEW vw_dados_corretoras AS
        SELECT mes_ref, corretora, ticker
        FROM raw_recomendacoes
        ORDER BY mes_ref DESC, corretora, ticker
    """)

    # View para listar as corretoras rastreadas por mês
    conn.execute("""
        CREATE OR REPLACE VIEW vw_corretoras_por_mes AS
        WITH corretoras_mes AS (
            SELECT DISTINCT mes_ref, corretora 
            FROM raw_recomendacoes
        )
        SELECT 
            mes_ref,
            COUNT(corretora) as total_corretoras,
            LIST(corretora ORDER BY corretora) as lista_corretoras
        FROM corretoras_mes
        GROUP BY mes_ref
        ORDER BY mes_ref DESC
    """)

    # View para consultar carteira consolidada (Top 10)
    conn.execute("""
        CREATE OR REPLACE VIEW vw_carteira_consolidada AS
        WITH ranking AS (
            SELECT
                r.mes_ref,
                r.ticker,
                COUNT(DISTINCT r.corretora) AS votos,
                COALESCE(m.volume_medio_diario, 0) AS volume_desempate,
                ROW_NUMBER() OVER (
                    PARTITION BY r.mes_ref
                    ORDER BY COUNT(DISTINCT r.corretora) DESC, COALESCE(m.volume_medio_diario, 0) DESC
                ) AS rank
            FROM raw_recomendacoes r
            LEFT JOIN dados_mercado m
                ON r.ticker = m.ticker
            GROUP BY
                r.mes_ref,
                r.ticker,
                m.volume_medio_diario
        )
        SELECT mes_ref, rank, ticker, votos, volume_desempate
        FROM ranking
        WHERE rank <= 10
        ORDER BY mes_ref DESC, rank ASC
    """)

    # View para consultar as alterações na carteira de cada corretora (Entradas, Saídas e Manutenções)
    conn.execute("""
        CREATE OR REPLACE VIEW vw_alteracoes_carteira AS
        WITH carteiras AS (
            SELECT 
                mes_ref,
                corretora,
                LIST(ticker ORDER BY ticker) AS tickers_atual
            FROM raw_recomendacoes
            GROUP BY mes_ref, corretora
        ),
        carteiras_com_lag AS (
            SELECT 
                mes_ref,
                corretora,
                tickers_atual,
                COALESCE(LAG(tickers_atual) OVER (PARTITION BY corretora ORDER BY mes_ref), []) AS tickers_anterior
            FROM carteiras
        ),
        desagregado AS (
            SELECT mes_ref, corretora, unnest(tickers_atual) as ticker, tickers_anterior as tickers_comparacao, 'atual' as source
            FROM carteiras_com_lag
            UNION ALL
            SELECT mes_ref, corretora, unnest(tickers_anterior) as ticker, tickers_atual as tickers_comparacao, 'anterior' as source
            FROM carteiras_com_lag
        )
        SELECT DISTINCT
            mes_ref,
            corretora,
            ticker,
            CASE 
                WHEN source = 'atual' AND NOT list_contains(tickers_comparacao, ticker) THEN 'Entrada'
                WHEN source = 'atual' AND list_contains(tickers_comparacao, ticker) THEN 'Manutenção'
                WHEN source = 'anterior' AND NOT list_contains(tickers_comparacao, ticker) THEN 'Saída'
            END AS status
        FROM desagregado
        WHERE status IS NOT NULL
        ORDER BY mes_ref DESC, corretora, status, ticker
    """)


def salvar_resultados_parciais(
    dados: list[dict[str, Any]], mes_ref: str, db_path: str, append: bool = False
) -> None:
    """
    Converte a lista estruturada pelo LLM em DataFrame e persiste no DuckDB.

    Args:
        dados (list[dict[str, Any]]): Carteiras.
            Exemplo: [{'corretora': 'Nome', 'tickers': ['TICKER']}]
        mes_ref (str): Mês de referência no formato (ex: '2023-08')
        db_path (str): Caminho físico para o banco local do DuckDB
        append (bool): Se verdadeiro, adiciona os dados sem limpar a tabela. Padrão: False.
    """
    logger.info(
        f"Salvando {len(dados)} recomendação(ões) no banco {db_path} (ref: {mes_ref})"
    )

    if not dados:
        logger.warning("Nenhum dado estruturado para salvar.")
        return

    # Achata a estrutura aninhada de listas em um formato tabular para o DataFrame
    linhas = [
        {"corretora": carteira["corretora"], "ticker": ticker, "mes_ref": mes_ref}
        for carteira in dados
        for ticker in carteira.get("tickers", [])
    ]

    df = pd.DataFrame(linhas)

    with duckdb.connect(db_path) as conn:
        _inicializar_banco(conn)

        if not append:
            # Limpa os dados se append for falso
            conn.execute("DELETE FROM raw_recomendacoes")
        
        # Insere os dados diretamente no DuckDB lendo a partir do DataFrame pandas.
        # O DuckDB possui integração zero-copy direta para esse caso.
        logger.debug(
            f"Inserindo {len(df)} linha(s) tabular(es) na tabela raw_recomendacoes"
        )
        conn.execute("INSERT INTO raw_recomendacoes SELECT * FROM df")

    logger.info("Recomendações persistidas com sucesso no banco analítico.")


def obter_meses_salvos(db_path: str) -> set[str]:
    """Retorna um conjunto (set) de todos os meses de referência que já estão salvos no banco.

    Args:
        db_path (str): Caminho físico para o banco local do DuckDB

    Returns:
        set[str]: Conjunto de strings no formato 'AAAA-MM'
    """
    import os
    if not os.path.exists(db_path):
        return set()

    with duckdb.connect(db_path) as conn:
        try:
            # Pega meses distintos. fetchall retorna lista de tuplas ex: [('2023-01',), ('2023-02',)]
            resultado = conn.execute("SELECT DISTINCT mes_ref FROM raw_recomendacoes").fetchall()
            return {r[0] for r in resultado if r[0]}
        except duckdb.CatalogException:
            # Tabela raw_recomendacoes pode não existir ainda
            return set()


def gerar_carteira_consenso(db_path: str, mes_ref: str = None) -> pa.Table:
    """Calcula o consenso agrupando por ticker usando SQL no DuckDB.

    Desempata os ativos com mesmo número de votos utilizando o volume_medio_diario.

    Args:
        db_path (str): Caminho para o banco local do DuckDB
        mes_ref (str, optional): Mês de referência no formato (ex: '2023-08'). Se None, usa todos.

    Returns:
        pa.Table: Tabela no formato PyArrow com os tickers e a contagem.
    """
    logger.info(f"Gerando rank de consenso a partir do banco {db_path}" + (f" para {mes_ref}" if mes_ref else ""))

    where_clause = f"WHERE mes_ref = '{mes_ref}'" if mes_ref else ""

    query = f"""
        SELECT ticker, votos, volume_desempate
        FROM vw_carteira_consolidada
        {where_clause}
        ORDER BY rank ASC
    """

    with duckdb.connect(db_path) as conn:
        logger.debug("Processando engine de cálculo via query otimizada.")
        _inicializar_banco(conn)
        # Retorna diretamente em PyArrow. Ideal para altíssima performance e compatível
        # nativamente com sistemas modernos de manipulação de dados em memória.
        resultado_arrow = conn.execute(query).to_arrow_table()

    logger.info(
        f"Consenso gerado com sucesso: {resultado_arrow.num_rows} ativos pontuados."
    )
    return resultado_arrow
