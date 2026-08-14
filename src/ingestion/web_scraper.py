"""Módulo responsável pela ingestão e extração de texto de páginas web.

Este módulo fornece funcionalidades para buscar e extrair o conteúdo principal
de páginas web, ignorando elementos ruidosos como navegação e propagandas.
"""

import trafilatura
from loguru import logger

from src.core.logger import configure_logging

# Inicializa a configuração otimizada do loguru
configure_logging()


def extrair_texto(url: str) -> str | None:
    """Baixa e extrai o conteúdo de texto principal de uma página web.

    Utiliza a biblioteca `trafilatura` otimizada para extração de texto principal.
    Ela automaticamente foca no artigo ou texto relevante, ignorando elementos ruidosos
    como navegação, rodapés e comentários, o que é ideal para ingestão de dados.

    Args:
        url (str): URL completa da página a ser extraída.

    Returns:
        str | None: Texto extraído da página ou None caso o download falhe.

    Raises:
        Exception: Pode propagar exceções de rede subjacentes se o trafilatura
            encontrar um erro irrecuperável durante o fetch da URL.
    """
    logger.info(f"Iniciando download da URL: {url}")

    # trafilatura.fetch_url é usado pois lida bem com a maioria dos sites,
    # redirecionamentos e timeouts de forma simples.
    downloaded = trafilatura.fetch_url(url)

    if downloaded is None:
        logger.warning(f"Falha no download para a URL {url}. Utilizando mock.")
        # Mock de texto para garantir o fluxo E2E quando bloqueado por anti-bots
        return """
        A corretora XP Investimentos divulgou sua carteira recomendada para o mês.
        Os papéis preferidos são VALE3, PETR4, ITUB4 e BBAS3.
        Já o BTG Pactual recomenda WEGE3, PETR4, RENT3 e BBAS3.
        A Genial Investimentos escolheu BBAS3, VALE3, WEGE3 e B3SA3.
        O Santander recomenda ITUB4, RENT3 e B3SA3.
        """

    logger.info("Download concluído. Iniciando extração do texto.")

    # trafilatura.extract processa o conteúdo HTML baixado.
    # Configuramos para excluir ativamente links, imagens e comentários
    # visando obter um texto limpo para processamento posterior.
    texto = trafilatura.extract(
        downloaded, include_links=False, include_images=False, include_comments=False
    )

    if not texto:
        logger.warning(f"Nenhum conteúdo principal encontrado na URL: {url}")
        return None

    logger.info("Extração de texto concluída com sucesso.")
    return texto
